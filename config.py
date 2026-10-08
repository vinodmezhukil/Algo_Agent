"""
Configuration for the NIFTY 50 trading agent.

IMPORTANT:
- Never commit real API keys/secrets to version control.
- Prefer loading these from environment variables in production
  (os.environ.get(...)) rather than hardcoding them here.
"""

import os

# ---- Kite Connect API credentials ----
# Get these from https://developers.kite.trade/ after subscribing
# to the Kite Connect API (₹2000/month, separate from your regular
# Zerodha trading account).
API_KEY = os.environ.get("KITE_API_KEY", "svijmckulq7rxc90")
API_SECRET = os.environ.get("KITE_API_SECRET", "5fx0jo8mezd192j42pzdta0bgj9z2dfh")
ACCESS_TOKEN_FILE = "access_token.txt"  # generated daily via login flow

# ---- Instrument & Options Config ----
# NIFTY 50 index itself cannot be traded directly. Common proxies:
#   - NIFTY 50 options (NFO segment) by strike
#   - NIFTY 50 futures (NFO segment)
#   - NIFTYBEES / other index ETFs (NSE cash segment)
TRADING_SYMBOL = "NIFTY 50"   # <-- update to current month's contract / underlying
EXCHANGE = "NSE"                   # NFO for futures/options, NSE for ETFs/spot index
SIGNAL_SYMBOL = "NIFTY 50"         # index symbol used for signal generation
SIGNAL_EXCHANGE = "NSE"
STOCK = "NIFTY"                    # "NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX"
OPTIONS_EXCHANGE = "NFO"
STRIKE_STEP = 50                   # 50 for NIFTY, 100 for BANKNIFTY

LOT_SIZE = 65          # NIFTY lot size (check current exchange lot size)
MAX_LOTS = 1            # position size in lots (if > 1: sells 1 lot on target, remaining trail with no target)
otm = 0                 # Strike offset from ATM: 0 for ATM, +50 for 1-strike OTM CE, etc.
papertrading = 0        # 0 = paper trading (simulated), 1 = real live trades sent to broker
producttype = "intraday_fno"  # "intraday_eq", "positional_eq", "intraday_fno", "positional_fno"

# ---- Telegram Alerts ----
ENABLE_TELEGRAM_ALERTS = os.environ.get("ENABLE_TELEGRAM_ALERTS", "True").lower() in ("true", "1", "yes")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "7863022120:AAGtSbom4q714ozMjpY3Jn5zEIksGnlMbxw")
TELEGRAM_CHAT_IDS = [int(x.strip()) for x in os.environ.get("TELEGRAM_CHAT_IDS", "1484937732").split(",") if x.strip()]


# ---- Strategy parameters ----
SHORT_WINDOW = 9         # short SMA period (in candles)
LONG_WINDOW = 21         # long SMA period (in candles)
CANDLE_INTERVAL = "minute"   # kite historical data interval
POLL_SECONDS = 60        # how often the main loop checks for a new candle
EXIT_CHECK_SECONDS = 60  # how often open positions are checked against SL/target using live price

# ---- Strategy v2 parameters: EMA/ADX/RSI scalping system ----
EMA_SHORT = 10
EMA_LONG = 50
ADX_PERIOD = 14
ADX_THRESHOLD = 20        # only trade when ADX > this (trending market)
RSI_PERIOD = 14           # RSI > 50 = bullish bias, RSI < 50 = bearish bias
STRATEGY_V2_INTERVAL = "minute"  # 1-minute candles

# Exit management (in option premium points)
STOP_LOSS_POINTS = 5
TARGET_POINTS = 15
TRAILING_STOP_ENABLED = True

# ---- Strategy v3 parameters: FVG rejection system ----
FVG_INTERVAL = "minute"     # 1-minute candles for signal detection on spot
FVG_SL_BUFFER_POINTS = 1    # SL buffer in option points beyond FVG risk
FVG_TARGET_POINTS = 10      # target in option points (premium)
FVG_MAX_SL_POINTS = 10      # hard cap: option SL distance from entry never exceeds this
FVG_TRAILING_STOP_ENABLED = True   # ratchet the option SL as option premium moves favorably

# ---- Risk management ----
MAX_DAILY_LOSS_RS = 1000        # stop trading for the day if breached
MAX_TRADES_PER_DAY = 10
TRADING_START = "09:20"          # avoid the first few volatile minutes
TRADING_END = "15:00"            # stop opening new positions before close
SQUARE_OFF_TIME = "15:15"        # force-close any open position

# ---- Kill switch ----
# Touch this file (e.g. `touch KILL_SWITCH`) to halt the agent immediately.
KILL_SWITCH_FILE = "KILL_SWITCH"

# ---- Logging ----
LOG_FILE = "trading_agent.log"
DRY_RUN = True  # <-- IMPORTANT: keep True until you've tested thoroughly.
                 # When True, orders are logged but NOT sent to Kite.
