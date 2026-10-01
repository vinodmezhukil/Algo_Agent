"""
Strategy logic, isolated from execution/risk code so it's easy to swap out.

To use your own strategy: replace the body of `generate_signal()`.
It must keep returning one of "BUY", "SELL", or "HOLD".
"""

import pandas as pd
import config


def compute_sma(candles: pd.DataFrame, window: int) -> pd.Series:
    return candles["close"].rolling(window=window).mean()


def generate_signal(candles: pd.DataFrame) -> str:
    """
    Simple SMA crossover:
      - short SMA crosses ABOVE long SMA  -> BUY
      - short SMA crosses BELOW long SMA  -> SELL
      - otherwise                          -> HOLD

    `candles` must be a DataFrame with a 'close' column, oldest first,
    as returned by Kite's historical data API.
    """
    if len(candles) < config.LONG_WINDOW + 1:
        return "HOLD"  # not enough data yet

    short_sma = compute_sma(candles, config.SHORT_WINDOW)
    long_sma = compute_sma(candles, config.LONG_WINDOW)

    prev_short, curr_short = short_sma.iloc[-2], short_sma.iloc[-1]
    prev_long, curr_long = long_sma.iloc[-2], long_sma.iloc[-1]

    crossed_up = prev_short <= prev_long and curr_short > curr_long
    crossed_down = prev_short >= prev_long and curr_short < curr_long

    if crossed_up:
        return "BUY"
    elif crossed_down:
        return "SELL"
    return "HOLD"
