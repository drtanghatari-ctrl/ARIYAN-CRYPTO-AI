# A007: Daily order-flow / positioning signals (pre-registered protocol)

Written BEFORE any micro (metrics / bookDepth) data was seen. Changing anything after the first run needs a new protocol.

## Question
Do Binance's own positioning statistics (taker buy/sell ratio, top-trader and all-account long/short ratios,
open interest) rank coins by next-day return well enough to earn a positive return after real costs?

## Data
`data/ariyan_micro_panel.zip` (built by `scripts/build_micro_panel.py`), plus `close.csv`, `funding.csv`, `volume.csv`
from `data/panel_wide`. Daily values are taken from 5-minute snapshots in UTC; the signal uses only snapshots up to the
day's close and earns the next day. Universe = union of daily top-K by volume (`select_micro_universe.py`).

## Candidates (6 trials, fixed now)
`ariyan_crypto/flow.py::flow_scores`: taker_follow_3d, taker_fade_3d, toptrader_follow, crowd_fade, oi_growth_fade, oi_growth_follow.
Each: eligible = top 20 by 30-day volume; `_long_short(score, quantile=0.3, gross=1.0)`; rebalanced daily. Nothing else is tried.

## Execution and period
Backtester defaults (5.5 bp fee + 5 bp slippage per side, funding charged, kill switch). Development = start of micro data
to 2025-10-31. The holdout (from 2025-11-01) is the one already locked in `results/holdout_lock.json`; this runner never reads it.
Note: that holdout was seen by earlier A005 work only for funding harvest, not for these signals.

## Pass marks (all required, best candidate by Sharpe)
1. Net Sharpe >= 0.5. 2. Deflated Sharpe prob >= 0.95 with N = 6 (variance = max of observed and sampling proxy).
3. Net-positive in >= 4 of 6 equal time blocks. 4. Positive with costs doubled. 5. Max drawdown no deeper than 15%.

## After the run
FAIL: family closed, no tuning; bookDepth is then used only to measure real slippage. PASS: single holdout run (new amendment), then
forward paper test. A pass never authorises live money.
