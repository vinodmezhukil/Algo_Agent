"""
Risk management: everything here exists to stop the agent from doing
something expensive and stupid. Do not weaken these checks to "make it
trade more" — that defeats the purpose.
"""

import os
import datetime as dt
import config


def kill_switch_active() -> bool:
    return os.path.exists(config.KILL_SWITCH_FILE)


def within_trading_hours() -> bool:
    now = dt.datetime.now().time()
    start = dt.datetime.strptime(config.TRADING_START, "%H:%M").time()
    end = dt.datetime.strptime(config.TRADING_END, "%H:%M").time()
    return start <= now <= end


def past_square_off_time() -> bool:
    now = dt.datetime.now().time()
    square_off = dt.datetime.strptime(config.SQUARE_OFF_TIME, "%H:%M").time()
    return now >= square_off


def daily_loss_breached(realized_pnl_today: float) -> bool:
    return realized_pnl_today <= -abs(config.MAX_DAILY_LOSS_RS)


def trade_count_exceeded(trades_today: int) -> bool:
    return trades_today >= config.MAX_TRADES_PER_DAY


def can_open_new_position(realized_pnl_today: float, trades_today: int) -> tuple[bool, str]:
    """Returns (allowed, reason_if_not)."""
    if kill_switch_active():
        return False, "Kill switch file present"
    if not within_trading_hours():
        return False, "Outside configured trading hours"
    if daily_loss_breached(realized_pnl_today):
        return False, f"Daily loss limit of Rs.{config.MAX_DAILY_LOSS_RS} breached"
    if trade_count_exceeded(trades_today):
        return False, f"Max trades per day ({config.MAX_TRADES_PER_DAY}) reached"
    return True, ""
