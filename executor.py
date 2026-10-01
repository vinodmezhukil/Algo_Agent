"""
Order placement and execution engine.

Supports:
1. NIFTY / BANKNIFTY / FINNIFTY / SENSEX Option trading by strike (ATM / ITM / OTM CE/PE)
   integrated from order_palcing.py.
2. Direct spot and futures order placement on NSE/NFO.
3. Dry-run and Paper trading support.
4. Telegram alert notifications on order entries, exits, and errors.
"""

import logging
import datetime as dt
import time
import requests
from decimal import Decimal

import config
import helper_zerodha as helper

logger = logging.getLogger("nifty_agent")

trade_id = 0
order_id = 0
# =====================================================================
# Telegram Alerts
# =====================================================================

def send_telegram_alert(message: str) -> None:
    """Send alert message to configured Telegram chats."""
    if not getattr(config, "ENABLE_TELEGRAM_ALERTS", True):
        return

    bot_token = getattr(config, "TELEGRAM_BOT_TOKEN", None)
    chat_ids = getattr(config, "TELEGRAM_CHAT_IDS", [])

    if not bot_token or not chat_ids:
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    for chat_id in chat_ids:
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
        }
        try:
            resp = requests.post(url, json=payload, timeout=15)
            if resp.status_code == 200:
                logger.debug(f"Telegram alert sent to {chat_id}")
            else:
                logger.warning(f"Telegram alert failed for {chat_id}: {resp.text}")
        except Exception as e:
            logger.warning(f"Telegram alert connection error for {chat_id}: {e}")
        time.sleep(0.05)


# =====================================================================
# Strike & Option Contract Resolution
# =====================================================================

def get_spot_ltp(kite, stock: str = "NIFTY") -> float:
    """
    Fetch the live spot price of the underlying index (e.g. NIFTY 50).
    Falls back to helper.getQuotes if kite LTP is unavailable.
    """
    spot_symbol = helper.getIndexSpot(stock)  # e.g. "NSE:NIFTY 50"
    if kite is not None:
        try:
            quote = kite.ltp([spot_symbol])
            if spot_symbol in quote and "last_price" in quote[spot_symbol]:
                return float(quote[spot_symbol]["last_price"])
        except Exception as e:
            logger.warning(f"Failed to fetch spot LTP via kite.ltp({spot_symbol}): {e}")

    # Fallback to helper_zerodha cache
    local_ltp = helper.getQuotes(spot_symbol)
    if local_ltp > 0:
        return float(local_ltp)

    logger.error(f"Could not retrieve spot LTP for {spot_symbol}")
    return 0.0


def get_expiry(stock: str = "NIFTY") -> str:
    """Get the current expiry date string from helper."""
    if stock == "NIFTY":
        return helper.getNiftyExpiryDate()
    elif stock == "SENSEX":
        return helper.getSensexExpiryDate()
    elif stock == "BANKNIFTY":
        return helper.getBankNiftyExpiryDate()
    elif stock == "FINNIFTY":
        return helper.getFinNiftyExpiryDate()
    else:
        return helper.getStockExpiryDate()


def get_atm_strike(spot_price: float, stock: str = "NIFTY") -> int:
    """Calculate the closest ATM strike price based on the underlying index step."""
    if stock in ("BANKNIFTY", "SENSEX"):
        step = 100
    else:
        step = getattr(config, "STRIKE_STEP", 50)

    return int(round(spot_price / step) * step)


def get_option_contract(
    kite=None,
    stock: str = "NIFTY",
    ce_pe: str = "CE",
    otm_offset: int = 0,
    spot_price: float = None,
    position: object = (),
) -> dict:
    """
    Resolve the option contract (strike, tradingsymbol, exchange) for a given stock and CE/PE.
    
    otm_offset:
      - For CE: strike = ATM + otm_offset (e.g. +50 is 1 strike OTM, 0 is ATM, -50 is ITM)
      - For PE: strike = ATM - otm_offset (e.g. +50 is 1 strike OTM, 0 is ATM, -50 is ITM)
    """
    stock = stock or getattr(config, "STOCK", "NIFTY")
    if spot_price is None or spot_price <= 0:
        spot_price = get_spot_ltp(kite, stock)

    atm_strike = get_atm_strike(spot_price, stock)
    ce_pe = ce_pe.upper()

    if ce_pe == "CE":
        target_strike = atm_strike + otm_offset
    else:
        target_strike = atm_strike - otm_offset

    int_expiry = get_expiry(stock)
    print("Strick", stock, int_expiry, target_strike, ce_pe)
    print("position", position)
    if stock == "SENSEX":
        full_symbol = helper.getOptionFormat_bse(stock, int_expiry, target_strike, ce_pe)
    else:
        full_symbol = helper.getOptionFormat(stock, int_expiry, target_strike, ce_pe)

    # full_symbol is e.g. "NFO:NIFTY2692225600CE"
    if ":" in full_symbol:
        exchange, tradingsymbol = full_symbol.split(":", 1)
    else:
        exchange = getattr(config, "OPTIONS_EXCHANGE", "NFO")
        tradingsymbol = full_symbol

    return {
        "stock": stock,
        "exchange": exchange,
        "tradingsymbol": tradingsymbol,
        "full_symbol": full_symbol,
        "strike": target_strike,
        "atm_strike": atm_strike,
        "expiry": int_expiry,
        "ce_pe": ce_pe,
        "spot_price": spot_price,
    }


def get_option_ltp(kite, exchange: str, tradingsymbol: str) -> float:
    """Fetch live option contract LTP."""
    full_symbol = f"{exchange}:{tradingsymbol}"
    if kite is not None:
        try:
            quote = kite.ltp([full_symbol])
            if full_symbol in quote and "last_price" in quote[full_symbol]:
                return float(quote[full_symbol]["last_price"])
        except Exception as e:
            logger.debug(f"Could not fetch option LTP via kite.ltp({full_symbol}): {e}")

    # Fallback to helper
    local_ltp = helper.getQuotes(full_symbol)
    return float(local_ltp) if local_ltp > 0 else 0.0


# =====================================================================
# Option Order Placement & Square-Off
# =====================================================================

def place_option_order(
    kite,
    signal_or_cepe: str,
    quantity: int = None,
    position: object = (),
    stock: str = None,
    otm_offset: int = None,
    spot_price: float = None,
    order_type: str = "MARKET",
    price: float = 0.0,
    sl: float = None,
    target: float = None,
    product_type: str = None,
    fvg: dict = None,
) -> dict:
    """
    Places an option order by strike.
    
    signal_or_cepe:
      - "BUY" / "CALL" / "CE" -> Buys the CE contract on calculated strike.
      - "SELL" / "PUT" / "PE" -> Buys the PE contract on calculated strike.
    """
    global trade_id, order_id
    stock = stock or getattr(config, "STOCK", "NIFTY")
    otm_offset = otm_offset if otm_offset is not None else getattr(config, "otm", 0)
    quantity = quantity or (config.LOT_SIZE * config.MAX_LOTS)

    # Map directional signal to option type
    sig = signal_or_cepe.upper()
    if sig in ("BUY", "CALL", "CE"):
        ce_pe = "CE"
    elif sig in ("SELL", "PUT", "PE"):
        ce_pe = "PE"
    else:
        raise ValueError(f"Unknown signal or option type: {signal_or_cepe}")

    contract = get_option_contract(
        kite=kite,
        stock=stock,
        ce_pe=ce_pe,
        otm_offset=otm_offset,
        spot_price=spot_price,
        position=position
    )
    if position is None or position == ():
        exchange = contract["exchange"]
        tradingsymbol = contract["tradingsymbol"]
        opt_ltp = get_option_ltp(kite, exchange, tradingsymbol)
        script_buy = "BUY"
        kite_script_buy = getattr(kite, "TRANSACTION_TYPE_BUY", "BUY") if kite else "BUY"

        # Compute option SL and Target based on option tradingsymbol LTP if not explicitly passed
        if sl is None or target is None:
            from strategy_v3 import compute_exit_levels
            calc_sl, calc_tgt = compute_exit_levels(
                sig, opt_ltp, fvg=fvg, sl_points=sl, target_points=target, is_option=True
            )
            if sl is None:
                sl = calc_sl
            if target is None:
                target = calc_tgt
    else:
        exchange = position.get("exchange", "NFO") if isinstance(position, dict) else "NFO"
        tradingsymbol = position["tradingsymbol"] if isinstance(position, dict) else str(position)
        contract = {
            "stock": stock,
            "exchange": exchange,
            "tradingsymbol": tradingsymbol,
            "full_symbol": f"{exchange}:{tradingsymbol}",
            "ce_pe": ce_pe,
            "spot_price": spot_price if spot_price is not None else 0.0,
        }
        opt_ltp = get_option_ltp(kite, exchange, tradingsymbol)
        script_buy = "SELL"
        kite_script_buy = getattr(kite, "TRANSACTION_TYPE_SELL", "SELL") if kite else "SELL"

    # Determine product code (MIS for intraday, NRML for carry-forward)
    ptype = product_type or getattr(config, "producttype", "intraday_fno")
    if "intraday" in ptype.lower():
        kite_product = getattr(kite, "PRODUCT_MIS", "MIS") if kite else "MIS"
    else:
        kite_product = getattr(kite, "PRODUCT_NRML", "NRML") if kite else "NRML"

    is_dry_run = config.DRY_RUN or (getattr(config, "papertrading", 0) == 0)
    time_str = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    trade_id = dt.datetime.now().strftime("%Y%m%d%H%M%S") if order_id == trade_id else trade_id
    ddate = dt.datetime.now().strftime('%Y-%m-%d')
    dtime = dt.datetime.now().strftime('%H:%M:%S')
    try:
        parent_id = trade_id if trade_id != 0 and script_buy == 'SELL' else 0
        trade_log = f"({trade_id}, '{ddate} {dtime}', '1', '{tradingsymbol}', '{script_buy}', {quantity}, 'MARKET', {opt_ltp}, 'FVG', 0, 'MIS', '0', {parent_id}),\n"
        with open("indicator_results_fvg_algo_agent.txt", "a") as f:
            f.write(trade_log)
        print(f"Trade logged to file", "success")
    except Exception as e:
        print(f"Error logging trade: {e}", "error")

    if is_dry_run:
        if script_buy == 'SELL':
            # Reset trade_id only if no remaining position
            if position is None or position == () or (isinstance(position, dict) and position.get("quantity", 0) <= quantity):
                trade_id = 0
                order_id = 0
        logger.info(
            f"[DRY RUN / PAPER] Placing {tradingsymbol[-2:]} {script_buy} order: "
            f"{quantity} x {tradingsymbol} on {exchange} @ ~{opt_ltp:.2f} "
            + (f"(Spot: {contract['spot_price']:.2f}, SL: {sl}, Target: {target})" if script_buy == 'BUY' else f"(Exit LTP: {opt_ltp:.2f})")
        )
        if script_buy == "BUY":
            alert_msg = (
                f"⚡ *[PAPER/DRY-RUN] Option BUY Placed*\n"
                f"• *Contract*: `{tradingsymbol}`\n"
                f"• *Type*: `{tradingsymbol[-2:]}` | *Strike*: `{tradingsymbol}`\n"
                f"• *Qty*: `{quantity}` | *Est LTP*: `₹{opt_ltp:.2f}`\n"
                f"• *SL*: `{sl}` | *Target*: `{target}`\n"
                f"• *Spot*: `{contract['spot_price']:.2f}`\n"
                f"• *Time*: `{time_str}`"
            )
        else:
            alert_msg = (
                f"🔔 *[PAPER/DRY-RUN] Option SELL Placed*\n"
                f"• *Contract*: `{tradingsymbol}`\n"
                f"• *Qty*: `{quantity}` | *Exit LTP*: `₹{opt_ltp:.2f}`\n"
                f"• *Time*: `{time_str}`"
            )
        send_telegram_alert(alert_msg)
        return {
            "status": "dry_run",
            "order_id": None,
            "contract": contract,
            "tradingsymbol": tradingsymbol,
            "exchange": exchange,
            "quantity": quantity,
            "transaction_type": script_buy,
            "entry_price": opt_ltp,
            "ce_pe": ce_pe,
            "sl": sl,
            "target": target,
        }

    try:
        order_id = kite.place_order(
            variety=kite.VARIETY_REGULAR,
            exchange=exchange,
            tradingsymbol=tradingsymbol,
            transaction_type=kite_script_buy,
            market_protection=-1,
            quantity=quantity,
            product=kite_product,
            order_type=kite.ORDER_TYPE_MARKET if order_type == "MARKET" else kite.ORDER_TYPE_LIMIT,
            price=price if order_type != "MARKET" else None,
        )
        logger.info(
            f"Option order placed: ID={order_id} ({tradingsymbol} {script_buy} {quantity} @ {opt_ltp})"
        )
        if script_buy == "BUY":
            alert_msg = (
                f"🚀 *Option BUY Executed (LIVE)*\n"
                f"• *Contract*: `{tradingsymbol}`\n"
                f"• *Type*: `{ce_pe}` | *Strike*: `{contract.get('strike', tradingsymbol)}`\n"
                f"• *Qty*: `{quantity}` | *LTP*: `₹{opt_ltp:.2f}`\n"
                f"• *Order ID*: `{order_id}`\n"
                f"• *SL*: `{sl}` | *Target*: `{target}`\n"
                f"• *Time*: `{time_str}`"
            )
        else:
            alert_msg = (
                f"🏁 *Option SELL Executed (LIVE)*\n"
                f"• *Contract*: `{tradingsymbol}`\n"
                f"• *Type*: `{ce_pe}`\n"
                f"• *Qty*: `{quantity}` | *LTP*: `₹{opt_ltp:.2f}`\n"
                f"• *Order ID*: `{order_id}`\n"
                f"• *Time*: `{time_str}`"
            )
        send_telegram_alert(alert_msg)
        return {
            "status": "placed",
            "order_id": order_id,
            "contract": contract,
            "tradingsymbol": tradingsymbol,
            "exchange": exchange,
            "quantity": quantity,
            "transaction_type": script_buy,
            "entry_price": opt_ltp,
            "ce_pe": ce_pe,
            "sl": sl,
            "target": target,
        }
    except Exception as e:
        logger.error(f"Option order placement FAILED for {tradingsymbol}: {e}")
        send_telegram_alert(f"❌ *Option Order FAILED*: {tradingsymbol} ({e})")
        return {"status": "error", "error": str(e), "contract": contract}


def square_off_option(
    kite,
    tradingsymbol: str,
    quantity: int = None,
    exchange: str = "NFO",
    entry_price: float = 0.0,
    reason: str = "EXIT",
    product_type: str = None,
) -> dict:
    """
    Exits/sells an open option position and calculates P&L.
    """
    quantity = quantity or (config.LOT_SIZE * config.MAX_LOTS)
    exit_ltp = get_option_ltp(kite, exchange, tradingsymbol)
    pnl = (exit_ltp - entry_price) * quantity if entry_price > 0 else 0.0

    ptype = product_type or getattr(config, "producttype", "intraday_fno")
    if "intraday" in ptype.lower():
        kite_product = getattr(kite, "PRODUCT_MIS", "MIS") if kite else "MIS"
    else:
        kite_product = getattr(kite, "PRODUCT_NRML", "NRML") if kite else "NRML"

    is_dry_run = config.DRY_RUN or (getattr(config, "papertrading", 0) == 0)
    time_str = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if is_dry_run:
        logger.info(
            f"[DRY RUN / PAPER] Exiting option {tradingsymbol}: "
            f"SELL {quantity} @ ~{exit_ltp:.2f} (Entry: {entry_price:.2f}, P&L: Rs.{pnl:.2f}, Reason: {reason})"
        )
        alert_msg = (
            f"🔔 *[PAPER/DRY-RUN] Option Exit*\n"
            f"• *Contract*: `{tradingsymbol}`\n"
            f"• *Action*: `SELL {quantity}` | *Exit LTP*: `₹{exit_ltp:.2f}`\n"
            f"• *Entry*: `₹{entry_price:.2f}` | *P&L*: `₹{pnl:.2f}`\n"
            f"• *Reason*: `{reason}`\n"
            f"• *Time*: `{time_str}`"
        )
        send_telegram_alert(alert_msg)
        return {
            "status": "dry_run",
            "order_id": None,
            "tradingsymbol": tradingsymbol,
            "quantity": quantity,
            "exit_price": exit_ltp,
            "pnl": pnl,
            "reason": reason,
        }

    try:
        order_id = kite.place_order(
            variety=kite.VARIETY_REGULAR,
            exchange=exchange,
            tradingsymbol=tradingsymbol,
            transaction_type=kite.TRANSACTION_TYPE_SELL,
            market_protection=-1,
            quantity=quantity,
            product=kite_product,
            order_type=kite.ORDER_TYPE_MARKET,
        )
        logger.info(
            f"Option exit placed: ID={order_id} ({tradingsymbol} SELL {quantity} @ {exit_ltp}, P&L={pnl:.2f})"
        )
        alert_msg = (
            f"🏁 *Option Exit Executed (LIVE)*\n"
            f"• *Contract*: `{tradingsymbol}`\n"
            f"• *Action*: `SELL {quantity}` | *Exit LTP*: `₹{exit_ltp:.2f}`\n"
            f"• *Order ID*: `{order_id}`\n"
            f"• *Entry*: `₹{entry_price:.2f}` | *P&L*: `₹{pnl:.2f}`\n"
            f"• *Reason*: `{reason}`\n"
            f"• *Time*: `{time_str}`"
        )
        send_telegram_alert(alert_msg)
        return {
            "status": "placed",
            "order_id": order_id,
            "tradingsymbol": tradingsymbol,
            "quantity": quantity,
            "exit_price": exit_ltp,
            "pnl": pnl,
            "reason": reason,
        }
    except Exception as e:
        logger.error(f"Option exit order FAILED for {tradingsymbol}: {e}")
        send_telegram_alert(f"❌ *Option Exit FAILED*: {tradingsymbol} ({e})")
        return {"status": "error", "error": str(e), "tradingsymbol": tradingsymbol}


# =====================================================================
# Standard Spot / Futures Order Placement (Backward Compatible)
# =====================================================================

def place_order(kite, transaction_type: str, quantity: int, is_option: bool = False, **kwargs):
    """
    Unified entry point.
    If is_option is True, delegates to place_option_order.
    Otherwise places regular order on config.TRADING_SYMBOL / config.EXCHANGE.
    """
    position = kwargs.pop('position', ())  # Extracts position if present, defaults to ()
    if is_option:
        return place_option_order(kite, transaction_type, quantity=quantity, position=position, **kwargs)

    if config.DRY_RUN:
        logger.info(
            f"[DRY RUN] Would place {transaction_type} order: "
            f"{quantity} x {config.TRADING_SYMBOL} on {config.EXCHANGE}"
        )
        return {"status": "dry_run", "order_id": None}

    try:
        order_id = kite.place_order(
            variety=kite.VARIETY_REGULAR,
            exchange=config.EXCHANGE,
            tradingsymbol=config.TRADING_SYMBOL,
            transaction_type=transaction_type,
            market_protection=-1,
            quantity=quantity,
            product=kite.PRODUCT_MIS,   # intraday; use PRODUCT_NRML for carry-forward
            order_type=kite.ORDER_TYPE_MARKET,
        )
        logger.info(f"Order placed: {order_id} ({transaction_type} {quantity})")
        return {"status": "placed", "order_id": order_id}
    except Exception as e:
        logger.error(f"Order placement FAILED: {e}")
        return {"status": "error", "error": str(e)}


def square_off_position(kite, current_qty: int, position=None):
    """current_qty > 0 means long -> SELL to close. < 0 means short -> BUY to close."""
    if current_qty == 0 and position is None:
        return {"status": "no_position"}
    if position is not None and isinstance(position, dict) and position.get("is_option", True):
        return place_order(kite, "SELL", abs(current_qty), is_option=True, position=position)
    transaction_type = "SELL" if current_qty > 0 else "BUY"
    return place_order(kite, transaction_type, abs(current_qty), is_option=False)

