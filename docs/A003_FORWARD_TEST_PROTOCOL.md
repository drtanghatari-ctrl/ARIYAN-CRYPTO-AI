# A003: Forward test of funding carry on data that did not exist when this was written

Frozen 2026-11-21. Window: **2026-11-22 to 2027-02-28 UTC (99 days)**. The panel used to select the candidate ends 2026-10-31,
so every window day is unseen by me and by the selection process. The forward result cannot be overfit by tuning.

## Candidates (2, fixed now; both use lookback 14, quantile 0.3, gross 1.0, daily rebalance)
- F1: the original 24 symbols (`scripts/download_binance.py` list).
- F2: full USDT-perp universe, eligible = top 50 by trailing 30-day volume (A004 candidate).
Signals use history before the window; positions start 2026-11-22. Same costs and kill switch as A001.

## Pass marks (per candidate)
1. Net total return over the window > 0.
2. Net annualised Sharpe >= 0.5.
3. Max drawdown no deeper than 15%.
4. Net total return still > 0 with fees and slippage doubled.
Reported for context, not a mark: BTC buy-and-hold over the same window.

## How it is run
After 2027-03-05 (the February archive file exists) re-run the downloaders, rebuild the panel, then
`python scripts/run_forward_carry.py --panel data/panel_wide`. The script refuses to run before the window ends,
refuses to run twice, and logs to the hash-chained registry.

## Power warning
99 days is short. A pass is encouraging evidence only and earns 6 more months of paper trading, never live money.
A fail closes carry on daily bars; the registry keeps the record.
