"""
Live trading loop for strategy_v3 (FVG rejection system) on Options.

This loop runs the Fair Value Gap (FVG) rejection strategy and executes
Option trades (CE/PE) on NFO:

  - It tracks FVG state THROUGH THE DAY on spot index (NIFTY 50) 1-minute
    candles (every FVG formed since market open, which ones are active).
  - When an FVG rejection trigger fires (CALL -> buy CE, PUT -> buy PE),
    it resolves the option contract tradingsymbol and enters a BUY order.
  - Target and Stop-loss are set directly in the OPTIONS TRADINGSYMBOL
    premium points (e.g. entry + 15 pts target, entry - SL pts stop-loss).
  - Trailing stop-loss is enabled (config.FVG_TRAILING_STOP_ENABLED):
    on every poll where the option trade is still open, update_trailing_stop()
    ratchets the option stop toward higher premiums by the trade's original
    risk distance. It only tightens, never loosens.
  - FAST EXIT CHECKS RUN EVERY 10 SECONDS (config.EXIT_CHECK_SECONDS)
    using the live option contract LTP from Kite/cache, while the spot
    candle/entry logic runs on its 60-second cadence.

Run once a day, after `python auth.py`, starting at/after market open:
    python main_v3.py
"""

import time
import logging
import datetime as dt
import pandas as pd

import config
import risk
import executor
from auth import get_kite_client
from strategy_v3 import DayFVGState, check_entry, compute_exit_levels, update_trailing_stop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("trading_agent_v3.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("nifty_agent_v3")

tradingsymbol = ""

def get_instrument_token(kite, exchange: str, symbol: str) -> int:
    matches = kite.ltp(f"{exchange}:{symbol}")
    return matches[f"{exchange}:{symbol}"]["instrument_token"]


def fetch_today_candles(kite, instrument_token: int) -> pd.DataFrame:
    """Pull every 1-minute candle from market open (09:15) to now, today."""
    now = dt.datetime.now()
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    data = kite.historical_data(instrument_token, market_open, now, config.FVG_INTERVAL)
    df = pd.DataFrame(data)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def check_and_exit_position(kite, position: dict, default_qty: int):
    """
    The fast (10-second) exit check. Fetches the live LTP for the traded
    option contract (tradingsymbol) and checks it against the open position's
    stop-loss and target in option premium points.

    Multi-lot scaling logic:
      - When TARGET is achieved:
        * If remaining_lots > 1:
          - Sells ONLY 1 LOT (LOT_SIZE).
          - Sets target to None for the remaining lots (no target).
          - Remaining lots continue trailing their stop-loss.
          - Position stays open with remaining lots/quantity.
        * If remaining_lots <= 1:
          - Sells all remaining quantity (full exit).
          - Position is closed (returns None).
      - When STOP_LOSS / TRAILING_STOP is hit:
        * Sells ALL remaining quantity (full exit).
        * Position is closed (returns None).

    Returns (position, realized_pnl_delta):
      - position is None if the trade was closed this check, otherwise
        the same dict (possibly with updated remaining quantity/target/trailing SL).
      - realized_pnl_delta is the P&L in rupees from closed quantity,
        or 0.0 if nothing closed.
    """
    if position is None:
        return position, 0.0

    tradingsymbol = position["tradingsymbol"]
    exchange = position.get("exchange", "NFO")
    price = executor.get_option_ltp(kite, exchange, tradingsymbol)

    if price <= 0:
        logger.warning(f"[10s check] Could not fetch LTP for option {tradingsymbol}; skipping check.")
        return position, 0.0

    side = position["side"]
    sl = position["stop_loss"]
    tgt = position.get("target")
    entry_price = position["entry_price"]
    lot_size = position.get("lot_size", getattr(config, "LOT_SIZE", 65))
    current_qty = position.get("quantity", default_qty)
    remaining_lots = position.get("remaining_lots", max(1, current_qty // lot_size))

    # 1. Stop-Loss / Trailing Stop Check (Full Exit of all remaining quantity)
    if price <= sl:
        reason = "TRAILING_STOP" if position.get("target_hit") or price > entry_price else "STOP_LOSS"
        logger.info(
            f"[10s check] Exiting ALL {current_qty} qty of {tradingsymbol} ({side}) @ ₹{price:.2f} ({reason}) | "
            f"Entry: ₹{entry_price:.2f} | SL: ₹{sl:.2f}"
        )
        executor.place_order(kite, "SELL", current_qty, is_option=True, position=position)
        pnl_pts = price - entry_price
        pnl_rs = pnl_pts * current_qty
        logger.info(f"Trade closed ({reason}). Realized P&L: ₹{pnl_rs:.2f} ({pnl_pts:+.2f} pts on {current_qty} qty)")
        return None, pnl_rs

    # 2. Target Check (Partial Exit of 1 lot if remaining_lots > 1, else Full Exit)
    if tgt is not None and price >= tgt:
        if remaining_lots > 1:
            sell_qty = lot_size
            remaining_qty = current_qty - sell_qty
            position["remaining_lots"] = remaining_lots - 1
            position["quantity"] = remaining_qty
            position["target"] = None        # No target for the remaining lots
            position["target_hit"] = True

            pnl_pts = price - entry_price
            pnl_rs = pnl_pts * sell_qty

            logger.info(
                f"[10s check] TARGET achieved @ ₹{price:.2f} (Target: ₹{tgt:.2f})! "
                f"Partial exit: Sold 1 lot ({sell_qty} qty). "
                f"Remaining: {position['remaining_lots']} lot(s) ({remaining_qty} qty) "
                f"with trailing SL=₹{sl:.2f} and NO further target."
            )
            executor.place_order(kite, "SELL", sell_qty, is_option=True, position=position)
            logger.info(f"Partial Target P&L: ₹{pnl_rs:.2f} ({pnl_pts:+.2f} pts on {sell_qty} qty)")

            # Continue trailing stop on remaining quantity
            new_sl = update_trailing_stop(position, price)
            if new_sl != sl:
                logger.info(
                    f"[10s check] Trailing stop moved to ₹{new_sl:.2f} for remaining {tradingsymbol} "
                    f"(LTP: ₹{price:.2f})"
                )

            return position, pnl_rs
        else:
            # Only 1 lot remaining: Full exit on target
            sell_qty = current_qty
            logger.info(
                f"[10s check] TARGET achieved @ ₹{price:.2f} (Target: ₹{tgt:.2f})! "
                f"Full exit: Sold {sell_qty} qty of {tradingsymbol} ({side}) | Entry: ₹{entry_price:.2f}"
            )
            executor.place_order(kite, "SELL", sell_qty, is_option=True, position=position)
            pnl_pts = price - entry_price
            pnl_rs = pnl_pts * sell_qty
            logger.info(f"Trade closed (TARGET). Realized P&L: ₹{pnl_rs:.2f} ({pnl_pts:+.2f} pts on {sell_qty} qty)")
            return None, pnl_rs

    # 3. Position Still Open: Ratchet trailing stop
    new_sl = update_trailing_stop(position, price)
    if new_sl != sl:
        logger.info(
            f"[10s check] Trailing stop moved to ₹{new_sl:.2f} for open {tradingsymbol} "
            f"(LTP: ₹{price:.2f})"
        )

    return position, 0.0


def main():
    logger.info("Starting NIFTY FVG rejection strategy (v3)")
    logger.info(f"DRY_RUN = {config.DRY_RUN}")
    logger.info(
        f"Entry/candle cycle: every {config.POLL_SECONDS}s | "
        f"Exit check cycle: every {config.EXIT_CHECK_SECONDS}s"
    )

    kite = get_kite_client()
    signal_token = get_instrument_token(kite, config.SIGNAL_EXCHANGE, config.SIGNAL_SYMBOL)

    LOT_SIZE = config.LOT_SIZE
    MAX_LOTS = config.MAX_LOTS
    qty = LOT_SIZE * MAX_LOTS

    state = DayFVGState()
    last_processed_idx = -1     # highest candle index already fed into state.update()
    current_day = dt.date.today()

    position = None             # dict: side, tradingsymbol, entry_price, stop_loss, target, ...
    trades_today = 0
    realized_pnl_today = 0.0    # stub — wire up to kite.orders()/trades() for real tracking
    squared_off_for_day = False
    last_candle_poll = 0.0      # time.time() of the last candle/entry cycle

    while True:
        try:
            if risk.kill_switch_active():
                logger.warning("Kill switch detected. Exiting loop.")
                break

            today = dt.date.today()
            if today != current_day:
                # New trading day: reset all day-scoped state
                logger.info(f"New day detected ({today}). Resetting FVG state.")
                state = DayFVGState()
                last_processed_idx = -1
                current_day = today
                trades_today = 0
                realized_pnl_today = 0.0
                squared_off_for_day = False
                position = None  # any overnight position should already be flat (intraday product)

            if risk.past_square_off_time() and not squared_off_for_day:
                if position is not None:
                    remaining_qty = position.get("quantity", qty)
                    logger.info(f"Square-off time reached. Closing open position of {remaining_qty} qty.")
                    opt_symbol = position["tradingsymbol"]
                    opt_exchange = position.get("exchange", "NFO")
                    exit_price = executor.get_option_ltp(kite, opt_exchange, opt_symbol)
                    executor.square_off_position(kite, remaining_qty, position)
                    pnl_pts = (exit_price - position["entry_price"]) if exit_price > 0 else 0.0
                    pnl_delta = pnl_pts * remaining_qty
                    realized_pnl_today += pnl_delta
                    logger.info(
                        f"Square-off completed for {opt_symbol} @ ₹{exit_price:.2f} | "
                        f"P&L: ₹{pnl_delta:.2f} | Total P&L: ₹{realized_pnl_today:.2f} | Trades: {trades_today}"
                    )
                    position = None
                squared_off_for_day = True
                break

            # ---- FAST PATH: runs every loop iteration (every EXIT_CHECK_SECONDS) ----
            position, pnl_delta = check_and_exit_position(kite, position, qty)
            realized_pnl_today += pnl_delta

            # ---- SLOW PATH: candle refresh + entry logic, only once per POLL_SECONDS ----
            now_ts = time.time()
            #print("now_ts", now_ts)
            if now_ts - last_candle_poll >= config.POLL_SECONDS:
                last_candle_poll = now_ts

                candles = fetch_today_candles(kite, signal_token)

                if len(candles) >= 3:
                    # Feed every not-yet-processed candle into the day's FVG state,
                    # in order, so mitigation/formation logic stays correct even if
                    # a poll cycle was missed.
                    for i in range(last_processed_idx + 1, len(candles)):
                        state.update(candles, i)
                    last_processed_idx = len(candles) - 1

                    if position is None:
                        allowed, why = risk.can_open_new_position(realized_pnl_today, trades_today)
                        if not allowed:
                            logger.info(f"Not trading right now: {why}")
                        else:
                            latest = candles.iloc[-1]
                            candle = {
                                "open": latest["open"], "high": latest["high"],
                                "low": latest["low"], "close": latest["close"],
                            }
                            print("candle", candle)
                            tracked = state.classify()
                            print("tracked", tracked)
                            side, fvg = check_entry(candle, tracked, require_full_body=True)
                            print("side", side)
                            print("fvg", fvg)
                            if side is not None:
                                fvg["traded"] = True
                                spot_entry_price = candle["close"]
                                open_txn = "BUY" if side == "CALL" else "SELL"
                                result = executor.place_order(
                                    kite, open_txn, qty, is_option=True,
                                    position=None, spot_price=spot_entry_price, fvg=fvg
                                )
                                if result["status"] in ("placed", "dry_run"):
                                    opt_symbol = result["tradingsymbol"]
                                    opt_exchange = result.get("exchange", "NFO")
                                    opt_entry = float(result.get("entry_price", 0.0))
                                    if opt_entry <= 0:
                                        opt_entry = executor.get_option_ltp(kite, opt_exchange, opt_symbol)

                                    sl = result.get("sl")
                                    tgt = result.get("target")
                                    if sl is None or tgt is None:
                                        sl, tgt = compute_exit_levels(
                                            side, opt_entry, fvg=fvg, is_option=True
                                        )

                                    risk_dist = abs(opt_entry - sl)
                                    total_lots = config.MAX_LOTS
                                    total_qty = config.LOT_SIZE * total_lots

                                    position = {
                                        "side": side,
                                        "ce_pe": result.get("ce_pe", "CE" if side == "CALL" else "PE"),
                                        "tradingsymbol": opt_symbol,
                                        "exchange": opt_exchange,
                                        "entry_price": opt_entry,
                                        "stop_loss": sl,
                                        "target": tgt,
                                        "target_hit": False,
                                        "total_lots": total_lots,
                                        "remaining_lots": total_lots,
                                        "lot_size": config.LOT_SIZE,
                                        "quantity": total_qty,
                                        "fvg": fvg,
                                        "extreme_price": opt_entry,
                                        "risk_distance": risk_dist,
                                        "is_option": True,
                                        "spot_entry_price": spot_entry_price,
                                    }
                                    trades_today += 1
                                    logger.info(
                                        f"Entered {opt_symbol} ({side}) {total_lots} lot(s) ({total_qty} qty) @ ₹{opt_entry:.2f} | "
                                        f"SL=₹{sl:.2f} Target=₹{tgt:.2f} | Spot: {spot_entry_price:.2f} "
                                        f"(FVG {fvg['direction']} {fvg['bottom']:.2f}-{fvg['top']:.2f})"
                                    )

        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
            # Continue rather than crash on a transient error (network blip,
            # momentary API hiccup). Repeated errors will show up in logs.
        #print("EXIT_CHECK_SECONDS", config.EXIT_CHECK_SECONDS)
        time.sleep(config.EXIT_CHECK_SECONDS)


if __name__ == "__main__":
    main()
