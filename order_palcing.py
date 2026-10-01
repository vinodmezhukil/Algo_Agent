"""
Option order placing and strike calculation utilities.
Integrated with executor.py for unified order routing and alerting.
"""

from decimal import Decimal
import time
import datetime as dt
import logging
import requests

import config
import helper_zerodha as helper
import executor

logger = logging.getLogger("nifty_agent")

total_loss = Decimal("0.0")
entry_price = Decimal("0.0")
tradeCEoption = ""
tradePEoption = ""
balance = Decimal("0.0")
LOT_SIZE = config.LOT_SIZE
MAX_LOTS = config.MAX_LOTS
qty = LOT_SIZE * MAX_LOTS

papertrading = getattr(config, "papertrading", 0)
producttype = getattr(config, "producttype", "intraday_fno")
otm = getattr(config, "otm", 0)


def send_telegram_alert(message: str):
    """Send message to Telegram using executor's alert handler."""
    return executor.send_telegram_alert(message)


def findStrikePriceATM(stock="NIFTY", cepe="CE", trade_time=None, sl=None, target=None, kite=None, spot_price=None):
    """
    Finds the ATM/OTM strike option for the given stock and places a BUY order.
    Returns the order dict / order_id.
    """
    global tradeCEoption, tradePEoption, total_loss, entry_price

    trade_time = trade_time or dt.datetime.now().strftime("%H:%M:%S")
    cepe = cepe.upper()

    res = executor.place_option_order(
        kite=kite,
        signal_or_cepe=cepe,
        quantity=qty,
        stock=stock,
        otm_offset=otm,
        spot_price=spot_price,
        sl=sl,
        target=target,
    )

    tradingsymbol = res.get("tradingsymbol", "")
    entry_price = Decimal(str(res.get("entry_price", 0.0)))
    order_id = res.get("order_id", 0)

    if cepe == "CE":
        tradeCEoption = tradingsymbol
        print(f"CE Entry OID: {order_id} ({tradingsymbol})")
    else:
        tradePEoption = tradingsymbol
        print(f"PE Entry OID: {order_id} ({tradingsymbol})")

    return order_id if order_id is not None else 0


def exitPosition(tradeOption, trade_time=None, reason="EXIT", kite=None):
    """
    Exits the open option position and logs P&L.
    """
    global total_loss, entry_price, tradeCEoption, tradePEoption

    trade_time = trade_time or dt.datetime.now().strftime("%H:%M:%S")

    # Extract exchange if prefix exists, e.g. "NFO:NIFTY..."
    if ":" in tradeOption:
        exchange, symbol = tradeOption.split(":", 1)
    else:
        exchange = getattr(config, "OPTIONS_EXCHANGE", "NFO")
        symbol = tradeOption

    res = executor.square_off_option(
        kite=kite,
        tradingsymbol=symbol,
        quantity=qty,
        exchange=exchange,
        entry_price=float(entry_price),
        reason=reason,
    )

    exit_price = Decimal(str(res.get("exit_price", 0.0)))
    pnl = Decimal(str(res.get("pnl", 0.0)))
    total_loss += pnl

    print("Entry:", entry_price)
    print("Exit:", exit_price)
    print("Trade P&L:", pnl)
    print("Total P&L:", total_loss)

    tradeCEoption = ""
    tradePEoption = ""
    order_id = res.get("order_id", 0)
    return order_id if order_id is not None else 0