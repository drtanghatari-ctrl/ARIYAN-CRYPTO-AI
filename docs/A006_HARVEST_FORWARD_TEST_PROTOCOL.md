# A006: Forward test of the hedged funding harvest (frozen 2026-11-22)

Window: **2026-11-22 to 2027-02-28 UTC (99 days)**, the same unseen window as A003.
Candidate (one, fixed): top 10 by trailing 30-day volume among coins with spot, entry hurdle 2 bp/day of trailing
14-day mean funding, exit when it turns <= 0, total notional 0.5 x min(1, held/5). Costs as in A005 (both legs).

## Pass marks (all required)
1. Net return over the window > 0.
2. Max drawdown no deeper than 3%.
3. Still net-positive with all costs doubled.
4. Net return beats cash on the same equity: at least 4% a year pro-rated to the window (about 1.1% for 99 days).
   Reason: the development edge decayed to about 2% a year on equity in 2023-2025. A hedged yield that does not beat cash
   is not worth the exchange and operational risk, whatever its Sharpe says.
Reported only: Sharpe, funding vs basis split, average coins held.

## Run
After 2027-03-05: re-run `download_binance_wide.py`, `download_binance_spot.py`, `build_panel.py --raw data/raw_wide --out data/panel_wide`,
`build_spot_panel.py`, then `python scripts/run_forward_harvest.py --panel data/panel_wide`. Refuses to run early or twice.
A pass allows a small, supervised live pilot decision with explicit human approval. A fail closes this harvest design.
