"""
Fair Value Gap (FVG) detection.

Definition used here (standard 3-candle FVG / imbalance):
  - BULLISH FVG at candle i: candle[i-2].high < candle[i].low
      zone = (bottom=candle[i-2].high, top=candle[i].low)
  - BEARISH FVG at candle i: candle[i-2].low > candle[i].high
      zone = (bottom=candle[i].high, top=candle[i-2].low)

A FVG is "formed" at the index of the 3rd candle (the one that leaves
the gap unfilled by candle i-1's body/wick).
"""

import pandas as pd


def detect_fvgs(df: pd.DataFrame) -> list[dict]:
    """
    df must have columns: date/time index, high, low (open/close optional).
    Returns a list of dicts, one per FVG found, in chronological order:
        {'formed_idx': i, 'formed_time': ..., 'direction': 'bullish'/'bearish',
         'top': float, 'bottom': float, 'mitigated': False}
    """
    fvgs = []
    highs = df['high'].values
    lows = df['low'].values
    times = df['date'].values if 'date' in df.columns else df.index.values

    for i in range(2, len(df)):
        # Bullish FVG: gap up, candle i-2 high below candle i low
        if highs[i - 2] < lows[i]:
            fvgs.append({
                'formed_idx': i,
                'formed_time': times[i],
                'direction': 'bullish',
                'top': lows[i],
                'bottom': highs[i - 2],
            })
        # Bearish FVG: gap down, candle i-2 low above candle i high
        elif lows[i - 2] > highs[i]:
            fvgs.append({
                'formed_idx': i,
                'formed_time': times[i],
                'direction': 'bearish',
                'top': lows[i - 2],
                'bottom': highs[i],
            })
    return fvgs


def classify_day_fvgs(active_fvgs: list[dict]) -> dict:
    """
    Given the list of currently-active (unmitigated) FVGs formed so far
    today, classify them into day-high / day-low / day-middle by price
    level. Returns a dict with keys 'high', 'low', 'middle' (any may be
    None if there aren't enough distinct FVGs).

    - day 'high' FVG  = the FVG with the highest top
    - day 'low' FVG   = the FVG with the lowest bottom
    - day 'middle' FVG = among the remaining FVGs, the one whose
      midpoint is closest to the midpoint of (day-high top, day-low bottom)
    """
    if not active_fvgs:
        return {'high': None, 'low': None, 'middle': None}

    day_high = max(active_fvgs, key=lambda f: f['top'])
    day_low = min(active_fvgs, key=lambda f: f['bottom'])

    remaining = [f for f in active_fvgs if f is not day_high and f is not day_low]

    middle = None
    if remaining:
        range_mid = (day_high['top'] + day_low['bottom']) / 2
        middle = min(remaining, key=lambda f: abs(((f['top'] + f['bottom']) / 2) - range_mid))

    return {'high': day_high, 'low': day_low, 'middle': middle}
