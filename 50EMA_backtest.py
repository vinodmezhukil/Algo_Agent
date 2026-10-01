import pandas as pd, numpy as np
from kiteconnect import KiteConnect
from datetime import datetime, timedelta
from auth import get_kite_client

kite = get_kite_client()

NIFTY, SL, TGT = 256265, 10.0, 20.0
TRAIL_TRIGGER, TRAIL_STEP = 10.0, 5.0   # tune these
COST_PTS = 7.0                          # futures; use ~1.0 for ATM options

# minute data: fetch in <=60-day chunks
end = datetime(2026, 9, 18, 15, 30)
df = pd.DataFrame(kite.historical_data(
    NIFTY, end - timedelta(days=50), end, "minute"))
df['date'] = pd.to_datetime(df['date'])

df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()

# Wilder ADX(14)
h, l, c = df['high'], df['low'], df['close']
tr = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
up, dn = h.diff(), -l.diff()
plus_dm  = np.where((up > dn) & (up > 0), up, 0.0)
minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
atr = pd.Series(tr).ewm(alpha=1/14, adjust=False).mean()
pdi = 100 * pd.Series(plus_dm).ewm(alpha=1/14, adjust=False).mean() / atr
mdi = 100 * pd.Series(minus_dm).ewm(alpha=1/14, adjust=False).mean() / atr
dx  = 100 * (pdi - mdi).abs() / (pdi + mdi)
df['adx'] = dx.ewm(alpha=1/14, adjust=False).mean()

df['long']  = (df.open < df.ema50) & (df.close > df.ema50) & (df.adx > 20)
df['short'] = (df.open > df.ema50) & (df.close < df.ema50) & (df.adx > 20)

trades, i = [], 0
while i < len(df) - 1:
    r = df.iloc[i]
    if not (r.long or r.short):
        i += 1; continue
    side  = 1 if r.long else -1
    entry = df.iloc[i+1].open
    stop  = entry - side*SL
    peak  = entry
    for j in range(i+1, len(df)):
        b = df.iloc[j]
        if b.date.date() != r.date.date() or b.date.time() >= pd.Timestamp("15:15").time():
            trades.append((r.date, side, entry, b.close, "EOD")); i = j; break
        # trailing stop
        peak = max(peak, b.high) if side == 1 else min(peak, b.low)
        if side*(peak - entry) >= TRAIL_TRIGGER:
            stop = max(stop, peak - side*TRAIL_STEP) if side == 1 \
                else min(stop, peak + TRAIL_STEP)
        hit_sl  = b.low <= stop if side == 1 else b.high >= stop
        hit_tgt = b.high >= entry + TGT if side == 1 else b.low <= entry - TGT
        if hit_sl:                      # SL first = conservative assumption
            trades.append((r.date, side, entry, stop, "SL")); i = j; break
        if hit_tgt:
            trades.append((r.date, side, entry, entry + side*TGT, "TGT")); i = j; break
    else:
        break

t = pd.DataFrame(trades, columns=['time','side','entry','exit','reason'])
t['pts'] = t.side * (t.exit - t.entry) - COST_PTS
print(f"Trades: {len(t)}  Win%: {(t.pts>0).mean():.1%}  "
      f"Net pts: {t.pts.sum():.1f}  Net Rs: {t.pts.sum()*65:,.0f}")
print(t.reason.value_counts())