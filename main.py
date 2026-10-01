"""
Main loop for the NIFTY 50 trading agent.

Run this during market hours (9:15 AM - 3:30 PM IST, Mon-Fri) after
generating today's access token via `python auth.py`.

Recommended: run under a process manager (systemd, supervisor, tmux)
or as a scheduled task that starts a few minutes after market open
and is killed a few minutes after market close. Do NOT rely on this
loop to know NSE holidays — check that separately before starting it.
"""

import time
import logging
import datetime as dt
import pandas as pd

import config
import strategy
import risk
import executor
from auth import get_kite_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("nifty_agent")


def fetch_recent_candles(kite, instrument_token: int) -> pd.DataFrame:
    to_date = dt.datetime.now()
    from_date = to_date - dt.timedelta(days=5)  # enough candles for the long SMA
    data = kite.historical_data(
        instrument_token, from_date, to_date, config.CANDLE_INTERVAL
    )
    return pd.DataFrame(data)


def get_instrument_token(kite, exchange: str, symbol: str) -> int:
    # In production, cache the full instrument dump instead of searching
    # every run — it changes rarely and the search is slow.
    matches = kite.ltp(f"{exchange}:{symbol}")
    return matches[f"{exchange}:{symbol}"]["instrument_token"]


def get_current_position_qty(kite) -> int:
    positions = kite.positions()["net"]
    for p in positions:
        if p["tradingsymbol"] == config.TRADING_SYMBOL:
            return p["quantity"]
    return 0


def main():
    logger.info("Starting NIFTY 50 trading agent")
    logger.info(f"DRY_RUN = {config.DRY_RUN}")

    kite = get_kite_client()
    signal_token = get_instrument_token(kite, config.SIGNAL_EXCHANGE, config.SIGNAL_SYMBOL)

    trades_today = 0
    realized_pnl_today = 0.0  # you'll want to compute this from kite.orders()/trades() in practice
    squared_off_for_day = False

    while True:
        try:
            if risk.kill_switch_active():
                logger.warning("Kill switch detected. Exiting loop.")
                break

            if risk.past_square_off_time() and not squared_off_for_day:
                qty = get_current_position_qty(kite)
                if qty != 0:
                    logger.info(f"Square-off time reached. Closing position of {qty}.")
                    executor.square_off_position(kite, qty)
                squared_off_for_day = True

            allowed, reason = risk.can_open_new_position(realized_pnl_today, trades_today)
            if not allowed:
                logger.info(f"Not trading right now: {reason}")
                time.sleep(config.POLL_SECONDS)
                continue

            candles = fetch_recent_candles(kite, signal_token)
            signal = strategy.generate_signal(candles)
            logger.info(f"Signal: {signal}")

            current_qty = get_current_position_qty(kite)
            order_qty = config.LOT_SIZE * config.MAX_LOTS

            if signal == "BUY" and current_qty <= 0:
                result = executor.place_order(kite, "BUY", order_qty)
                if result["status"] in ("placed", "dry_run"):
                    trades_today += 1
            elif signal == "SELL" and current_qty >= 0:
                result = executor.place_order(kite, "SELL", order_qty)
                if result["status"] in ("placed", "dry_run"):
                    trades_today += 1

        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
            # Deliberately continue rather than crash — a transient API
            # error shouldn't kill the process. Repeated errors will
            # naturally be visible in the logs.

        time.sleep(config.POLL_SECONDS)


if __name__ == "__main__":
    main()
