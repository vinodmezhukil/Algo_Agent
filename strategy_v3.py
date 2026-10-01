"""
Strategy v3: Fair Value Gap (FVG) rejection system.

Each trading day, we track every FVG formed so far and classify the
active (unmitigated) ones into day-high / day-low / day-middle by
price level (see fvg.classify_day_fvgs). For each of those three
tracked zones, we watch for a "rejection":

  - Candle's low touches down into/near the zone, then the candle
    CLOSES ABOVE the zone's top  -> CALL (long) entry
  - Candle's high pokes up into/near the zone, then the candle
    CLOSES BELOW the zone's bottom -> PUT (short) entry

Stop-loss:
  - CALL: 2 points below the FVG's bottom
  - PUT:  2 points above the FVG's top

Target: fixed 15 points (no trailing, per spec — different from
strategy_v2's trailing-stop system).

Only one position is held at a time. A FVG is used at most once for
an entry (marked 'traded') to avoid repeatedly re-triggering off the
same level. A FVG is dropped from consideration ("mitigated") once
price closes fully through it in the opposite direction, since a
fully-filled gap no longer represents unfilled imbalance.
"""

import config
from fvg import detect_fvgs, classify_day_fvgs


class DayFVGState:
    """Tracks FVGs for a single trading day as candles are processed."""

    def __init__(self):
        self.fvgs = []  # list of dicts, mutable (mitigated/traded flags added)

    def update(self, df_day, i):
        """
        Call once per new candle index i (within a single day's df).
        Detects a new FVG ending at i (if any), and updates
        mitigated status of existing FVGs against the latest close.
        """
        if i >= 2:
            highs = df_day['high'].values
            lows = df_day['low'].values
            if highs[i - 2] < lows[i]:
                self.fvgs.append({
                    'formed_idx': i, 'direction': 'bullish',
                    'top': lows[i], 'bottom': highs[i - 2],
                    'mitigated': False, 'traded': False,
                })
            elif lows[i - 2] > highs[i]:
                self.fvgs.append({
                    'formed_idx': i, 'direction': 'bearish',
                    'top': lows[i - 2], 'bottom': highs[i],
                    'mitigated': False, 'traded': False,
                })

        close = df_day['close'].values[i]
        for f in self.fvgs:
            if f['mitigated']:
                continue
            # Fully filled: price closed through the entire zone
            if f['direction'] == 'bullish' and close < f['bottom']:
                f['mitigated'] = True
            elif f['direction'] == 'bearish' and close > f['top']:
                f['mitigated'] = True

    def active_fvgs(self):
        return [f for f in self.fvgs if not f['mitigated']]

    def classify(self):
        return classify_day_fvgs(self.active_fvgs())


def check_entry(candle, tracked_fvgs: dict, require_full_body: bool = True):
    """
    candle: dict-like with 'open', 'high', 'low', 'close'
    tracked_fvgs: {'high': fvg_or_None, 'low': fvg_or_None, 'middle': fvg_or_None}

    Returns (side, fvg) if a rejection entry triggers, else (None, None).
    side is "CALL" or "PUT". Checks day-high, day-low, day-middle in
    that order and takes the first valid, not-yet-traded signal.

    require_full_body controls how strict the "rejection" test is:

    - False (wick-touch mode): only the candle's shadow needs to dip
      into the zone before the close breaks out the other side —
      candle['low'] <= top and candle['close'] > top for a CALL. A
      candle with a long wick and a tiny real body can trigger this.

    - True (full candle-body rejection, the default): the candle's
      OPEN must also be on/inside the zone, so the entire real body
      — not just a shadow — crosses the level. This filters out the
      wick-only pokes that made the wick-touch version fire ~26
      times/day, and is intended to only catch candles that actually
      close decisively through the level with body conviction.
    """
    for label in ('high', 'low', 'middle'):
        f = tracked_fvgs.get(label)
        if f is None or f['traded']:
            continue

        top, bottom = f['top'], f['bottom']

        if require_full_body:
            # Rejection UP: candle opened at/below the top, closed above it (full body crosses)
            if candle['open'] <= top and candle['close'] > top:
                return "CALL", f
            # Rejection DOWN: candle opened at/above the bottom, closed below it (full body crosses)
            if candle['open'] >= bottom and candle['close'] < bottom:
                return "PUT", f
        else:
            # Rejection UP through the top -> CALL (wick-touch allowed)
            if candle['low'] <= top and candle['close'] > top:
                return "CALL", f
            # Rejection DOWN through the bottom -> PUT (wick-touch allowed)
            if candle['high'] >= bottom and candle['close'] < bottom:
                return "PUT", f

    return None, None


def compute_exit_levels(
    side: str,
    entry_price: float,
    fvg: dict = None,
    sl_points: float = None,
    target_points: float = None,
    is_option: bool = True,
):
    """
    Returns (stop_loss, target) prices for the given trade.

    When is_option=True (default for option trading):
      - entry_price is the option contract premium (e.g. ₹65.00).
      - Target: entry_price + FVG_TARGET_POINTS (higher premium).
      - Stop-loss: entry_price - sl_distance (capped by FVG_MAX_SL_POINTS).
      Applies for both CALL (CE) and PUT (PE) option buyers since buying an
      option gains as premium increases and loses as premium decreases.

    When is_option=False (spot/futures mode):
      - entry_price is the index spot price.
      - CALL: SL below FVG bottom / Target above entry.
      - PUT: SL above FVG top / Target below entry.
    """
    target_pts = target_points if target_points is not None else getattr(config, "FVG_TARGET_POINTS", 15)
    max_sl_pts = getattr(config, "FVG_MAX_SL_POINTS", 10)
    sl_buffer = getattr(config, "FVG_SL_BUFFER_POINTS", 2)

    if is_option:
        if sl_points is not None:
            sl_dist = sl_points
        elif fvg is not None and "top" in fvg and "bottom" in fvg:
            gap_width = fvg["top"] - fvg["bottom"]
            sl_dist = min(gap_width + sl_buffer, max_sl_pts) if gap_width > 0 else max_sl_pts
        else:
            sl_dist = max_sl_pts

        stop_loss = round(max(0.05, entry_price - sl_dist), 2)
        target = round(entry_price + target_pts, 2)
        return stop_loss, target

    # Spot / Futures mode (is_option=False)
    gap_width = (fvg["top"] - fvg["bottom"]) if (fvg and "top" in fvg and "bottom" in fvg) else 0.0
    wide_gap = gap_width > max_sl_pts

    if side == "CALL":
        if wide_gap or fvg is None:
            stop_loss = entry_price - max_sl_pts
        else:
            stop_loss = fvg["bottom"] - sl_buffer
        target = entry_price + target_pts
    else:  # PUT
        if wide_gap or fvg is None:
            stop_loss = entry_price + max_sl_pts
        else:
            stop_loss = fvg["top"] + sl_buffer
        target = entry_price - target_pts

    return stop_loss, target


def update_trailing_stop(position: dict, price: float) -> float:
    """
    Ratchets a trade's stop-loss in the trade's favor as price moves,
    keeping the SAME points-distance from entry that the trade started
    with (position['risk_distance'], set when the trade was opened —
    see compute_exit_levels). The stop only ever tightens; it never
    loosens back out.

    For options (is_option=True):
      - price is the option tradingsymbol's live LTP.
      - As option LTP rises, extreme_price rises and stop_loss ratchets up.

    position must have: 'stop_loss' (current), 'extreme_price' (best price seen
    so far in the trade's favor), 'risk_distance' (the original entry-to-stop distance).

    Mutates position in place and also returns the (possibly updated)
    stop_loss for convenience.
    """
    if not getattr(config, "FVG_TRAILING_STOP_ENABLED", True):
        return position['stop_loss']

    is_option = position.get("is_option", True)

    if is_option:
        # For option buyers (both CE and PE), rising premium is in trade's favor
        if price > position['extreme_price']:
            position['extreme_price'] = price
            new_stop = round(position['extreme_price'] - position['risk_distance'], 2)
            if new_stop > position['stop_loss']:
                position['stop_loss'] = new_stop
    else:
        # Spot / futures legacy mode
        if position.get('side') == "CALL":
            if price > position['extreme_price']:
                position['extreme_price'] = price
                new_stop = position['extreme_price'] - position['risk_distance']
                if new_stop > position['stop_loss']:
                    position['stop_loss'] = new_stop
        else:  # PUT
            if price < position['extreme_price']:
                position['extreme_price'] = price
                new_stop = position['extreme_price'] + position['risk_distance']
                if new_stop < position['stop_loss']:
                    position['stop_loss'] = new_stop

    return position['stop_loss']