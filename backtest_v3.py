import json
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
from strategy_v3 import DayFVGState, check_entry, compute_exit_levels

# ---- Load the same 1-minute candle data used for strategy_v2 ----
#with open('/mnt/user-data/tool_results/kite_get_historical_data_toolu_01U6pfog53FHjJAHuydnhZWP.json') as f:
#    wrapper = json.load(f)
#raw = json.loads(wrapper[0]['text'])
from kiteconnect import KiteConnect
import json
import time
from datetime import datetime, timedelta

def get_kite_client():
    """Load a saved access token and return a ready-to-use KiteConnect client."""
    kite = KiteConnect(api_key=config.API_KEY)
    with open(config.ACCESS_TOKEN_FILE) as f:
        access_token = f.read().strip()
    kite.set_access_token(access_token)
    return kite

kite = get_kite_client()

INSTRUMENT_TOKEN = 256265


def get_3_month_minute_data(instrument_token):

    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)
    raw = kite.historical_data(
        instrument_token=INSTRUMENT_TOKEN,
        from_date=start_date,
        to_date=end_date,
        interval="minute"
    )
    return raw

raw = get_3_month_minute_data(INSTRUMENT_TOKEN)

df = pd.DataFrame(raw)
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date').reset_index(drop=True)
df['day'] = df['date'].dt.date

print(f"Loaded {len(df)} 1-minute candles across {df['day'].nunique()} trading days")

REQUIRE_FULL_BODY = True  # True = full candle-body rejection, False = wick-touch (prior version)
print(f"Entry mode: {'FULL CANDLE-BODY rejection' if REQUIRE_FULL_BODY else 'wick-touch rejection'}")

LOT_SIZE = config.LOT_SIZE
MAX_LOTS = config.MAX_LOTS
qty = LOT_SIZE * MAX_LOTS
MAX_DAILY_LOSS_RS = config.MAX_DAILY_LOSS_RS
MAX_TRADES_PER_DAY = config.MAX_TRADES_PER_DAY

print(f"Risk Limits: Max Daily Loss = Rs.{MAX_DAILY_LOSS_RS:,.0f} | Max Trades/Day = {MAX_TRADES_PER_DAY}")

trades = []

for day, day_df in df.groupby('day'):
    day_df = day_df.reset_index(drop=True)
    state = DayFVGState()

    position = None  # dict: side, entry_price, entry_time, stop_loss, target, fvg
    day_realized_pnl = 0.0
    day_trades_count = 0

    for i in range(len(day_df)):
        row = day_df.iloc[i]
        candle = {'open': row['open'], 'high': row['high'], 'low': row['low'], 'close': row['close']}

        # Update FVG tracking (new FVG detection + mitigation check) first
        state.update(day_df, i)

        if position is not None:
            side = position['side']
            sl, tgt = position['stop_loss'], position['target']
            exit_price = None
            reason = None
            if side == "CALL":
                if row['low'] <= sl:
                    exit_price, reason = sl, "STOP_LOSS"
                elif row['high'] >= tgt:
                    exit_price, reason = tgt, "TARGET"
            else:  # PUT
                if row['high'] >= sl:
                    exit_price, reason = sl, "STOP_LOSS"
                elif row['low'] <= tgt:
                    exit_price, reason = tgt, "TARGET"

            if exit_price is not None:
                pnl_pts = (exit_price - position['entry_price']) if side == "CALL" \
                    else (position['entry_price'] - exit_price)
                pnl_rs = pnl_pts * qty
                day_realized_pnl += pnl_rs
                trades.append({
                    'day': day, 'side': side,
                    'entry_time': position['entry_time'], 'entry_price': position['entry_price'],
                    'exit_time': row['date'], 'exit_price': exit_price, 'exit_reason': reason,
                    'fvg_direction': position['fvg']['direction'],
                    'pnl_points': pnl_pts, 'pnl_rs': pnl_rs,
                })
                position = None

        if position is None:
            # Check risk limits before entering a new trade
            can_trade = True
            if MAX_TRADES_PER_DAY is not None and day_trades_count >= MAX_TRADES_PER_DAY:
                can_trade = False
            if MAX_DAILY_LOSS_RS is not None and day_realized_pnl <= -abs(MAX_DAILY_LOSS_RS):
                can_trade = False

            if can_trade:
                tracked = state.classify()
                side, fvg = check_entry(candle, tracked, require_full_body=REQUIRE_FULL_BODY)
                if side is not None:
                    fvg['traded'] = True
                    entry_price = row['close']
                    sl, tgt = compute_exit_levels(side, entry_price, fvg, is_option=False)
                    position = {
                        'side': side, 'entry_price': entry_price, 'entry_time': row['date'],
                        'stop_loss': sl, 'target': tgt, 'fvg': fvg,
                    }
                    day_trades_count += 1

    if position is not None:
        last = day_df.iloc[-1]
        side = position['side']
        exit_price = last['close']
        pnl_pts = (exit_price - position['entry_price']) if side == "CALL" \
            else (position['entry_price'] - exit_price)
        pnl_rs = pnl_pts * qty
        day_realized_pnl += pnl_rs
        trades.append({
            'day': day, 'side': side,
            'entry_time': position['entry_time'], 'entry_price': position['entry_price'],
            'exit_time': last['date'], 'exit_price': exit_price, 'exit_reason': "END_OF_DAY",
            'fvg_direction': position['fvg']['direction'],
            'pnl_points': pnl_pts, 'pnl_rs': pnl_rs,
        })

trades_df = pd.DataFrame(trades)
n = len(trades_df)

if n == 0:
    print("\nNo trades were generated by this strategy over the tested period.")
else:
    wins = trades_df[trades_df['pnl_rs'] > 0]
    losses = trades_df[trades_df['pnl_rs'] <= 0]
    win_rate = len(wins) / n * 100
    total_pnl = trades_df['pnl_rs'].sum()
    avg_win = wins['pnl_rs'].mean() if len(wins) else 0
    avg_loss = losses['pnl_rs'].mean() if len(losses) else 0

    trades_df['cum_pnl'] = trades_df['pnl_rs'].cumsum()
    running_max = trades_df['cum_pnl'].cummax()
    max_dd = (trades_df['cum_pnl'] - running_max).min()

    target_hits = (trades_df['exit_reason'] == 'TARGET').sum()
    sl_hits = (trades_df['exit_reason'] == 'STOP_LOSS').sum()
    eod_hits = (trades_df['exit_reason'] == 'END_OF_DAY').sum()
    calls = (trades_df['side'] == 'CALL').sum()
    puts = (trades_df['side'] == 'PUT').sum()

    print(f"\n===== BACKTEST: FVG Rejection Strategy (day high/low/middle), 1-min, SL=2pt buffer/Target=15 =====")
    print(f"Risk limits: Max Daily Loss = Rs.{MAX_DAILY_LOSS_RS:,.0f} | Max Trades/Day = {MAX_TRADES_PER_DAY}")
    print(f"Total trades: {n}  (CALL: {calls}, PUT: {puts})")
    print(f"Trading days covered: {trades_df['day'].nunique()} / {df['day'].nunique()}")
    print(f"Win rate: {win_rate:.1f}%  ({len(wins)} wins / {len(losses)} losses)")
    print(f"Exits -> Target: {target_hits}   Stop-loss: {sl_hits}   End-of-day: {eod_hits}")
    print(f"Total P&L: Rs.{total_pnl:,.0f}")
    print(f"Avg win: Rs.{avg_win:,.0f}   Avg loss: Rs.{avg_loss:,.0f}")
    print(f"Max drawdown: Rs.{max_dd:,.0f}")
    print(f"Avg P&L per trade: Rs.{total_pnl/n:,.0f}")
    print(f"Avg trades per day: {n / trades_df['day'].nunique():.1f}")

    out_name = 'backtest_v3_fullbody_trades.csv' if REQUIRE_FULL_BODY else 'backtest_v3_trades.csv'
    #trades_df.to_csv(f'/home/claude/nifty_agent/{out_name}', index=False)
    print(f"\nTrade log saved to {out_name}")
