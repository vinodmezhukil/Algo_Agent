# NIFTY 50 Trading Agent (Kite Connect)

A scaffold for an automated trading agent on NIFTY 50, using Zerodha's
Kite Connect API. Ships with a placeholder SMA-crossover strategy —
replace `strategy.py` with your own logic.

## Setup

1. **Get Kite Connect API access**
   Subscribe at https://developers.kite.trade/ (₹2000/month, separate
   from your regular Zerodha account). You'll get an `api_key` and
   `api_secret`.

2. **Install dependencies**
   ```bash
   pip install kiteconnect pandas
   ```

3. **Set credentials** (environment variables, don't hardcode)
   ```bash
   export KITE_API_KEY="your_key"
   export KITE_API_SECRET="your_secret"
   ```

4. **Update `config.py`**
   - Current NIFTY futures contract symbol (rolls over monthly)
   - Current lot size (changes periodically — verify on NSE's site)
   - Risk limits to match what you're actually willing to lose

5. **Log in (once per trading day)**
   ```bash
   python auth.py
   ```
   Opens a login URL — authorize in browser, paste back the
   `request_token` from the redirect URL.

6. **Dry run first**
   With `DRY_RUN = True` in `config.py` (the default), run:
   ```bash
   python main.py
   ```
   Watch `trading_agent.log` for a few days. Confirm signals and
   would-be orders make sense before going live.

7. **Go live** — only after you've validated the above
   Set `DRY_RUN = False` in `config.py`.

## Safety features included

- **Dry run mode** — logs orders without sending them
- **Kill switch** — `touch KILL_SWITCH` in this folder halts the agent immediately
- **Daily loss limit** — stops opening new positions past a configured loss
- **Trade count cap** — limits trades per day
- **Trading hours window** — avoids the volatile open, stops new entries before close
- **Auto square-off** — force-closes any open position before market close

## What this scaffold does NOT do

- **Backtesting** — the SMA strategy here is illustrative, not validated.
  Backtest against historical data before trusting it with real money.
- **NSE holiday calendar** — you're responsible for not starting the
  agent on a market holiday.
- **Full P&L tracking** — `realized_pnl_today` in `main.py` is a stub;
  wire it up to `kite.orders()` / `kite.trades()` for real numbers.
- **Regulatory compliance** — SEBI has specific requirements for
  algorithmic trading by retail investors; check current rules before
  running this live. Requirements have been tightening — verify what
  applies to you before going live.
- **Unattended daily login** — Zerodha's auth flow requires a manual
  step (OTP/password) roughly once a day. You'll need to run `auth.py`
  each trading morning, or build a semi-automated wrapper around it.

## Disclaimer

This is a technical scaffold, not investment advice. Algorithmic
trading carries real risk of financial loss — backtested strategies
frequently underperform live due to slippage, latency, and changing
market conditions. Start with `DRY_RUN = True` and small position
sizes, and don't risk money you can't afford to lose.
