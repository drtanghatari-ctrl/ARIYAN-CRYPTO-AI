# Results log (development period 2020-01 to 2025-10-31; holdout 2025-11-01 to 2026-10-31 untouched)

## A001 funding carry: FAIL (family closed)
Best: lookback 14, quantile 0.3: net Sharpe 1.01, total return +149%, max drawdown -20.7%, 7 kill-switch halts.
Failed marks: deflated Sharpe 0.877 (needs 0.95) and max drawdown (needs <= 15%). Passed: Sharpe, 4/6 blocks, doubled costs.
Survivorship bias in the coin list means even this partial result is flattered.

## A002 reversal / momentum: FAIL
Reversal lost 79% to 95% after costs at every universe size (turnover about 0.5 to 0.9 of equity per day).
Momentum was marginal: best momentum28_N12 Sharpe 0.59, positive only at base costs, negative at 3x, DSR ~0.
No candidate passed any combination of all five marks.

Raw data: Binance archive; 5 days missing for every coin (2022-02-26..28, 2022-04-01..02).

## A004 wide-universe funding carry (859 USDT perps incl. 30 ended): FAIL
lookback 14, quantile 0.3, top-50 by volume: net Sharpe 0.63, return +87%, max drawdown -33%, 14 kill-switch halts, DSR 0.58 (N=7).
Passed: Sharpe >= 0.5, 4/6 blocks, doubled costs (+24%). Failed: DSR and max drawdown.
Same rule on the original 24 coins: Sharpe 1.12. The 0.5 Sharpe gap between the two is the survivorship bias in the hand-picked list.
Carry on daily bars is closed. Forward test A003 stays scheduled.

## A005 hedged funding harvest (long spot, short perp): PASS all six marks (development period)
Best: top-10 by volume, entry hurdle 2 bp/day. Net Sharpe 5.9 (daily closes), total return +36% on equity (5.5%/yr),
max drawdown -1.8%, DSR 1.00, 5 of 6 blocks positive, doubled costs still +17%, no year below -3%.
Diagnostics (information only): profit is entirely funding (+0.46 gross cumulative), basis P&L about zero, costs took 0.15.
Only 1 invested coin-day had a >2% basis move. None of the odd-basis coins (RAY, SC, FTT, CVX, STPT) were ever held.
**The edge has decayed:** 2020 +8.7%, 2021 +19.7%, 2022 -1.5%, 2023 +1.1%, 2024 +4.8%, 2025 +0.2%.
2023-2025 annualised return on equity: 2.1%, below cash yields. Passing the marks does not make it worth running.
Caveats: daily closes hide intraday basis spikes; exchange/counterparty risk and spot-side borrowing are not modelled.

## A005 holdout (2025-11-01 to 2026-10-31, run once per docs/A005_AMENDMENT_HOLDOUT.md): FAIL
Net return -0.4% (365 days), max drawdown -0.5%, doubled costs -1.7%, cash benchmark +4.0%. Average coins held: 2.6 (the entry rule
kept the strategy mostly in cash because funding stayed below the hurdle). Failed marks: net return > 0, doubled-cost positive, beats cash.
The strategy did not blow up, but the edge was not present in the last year. Holdout is now spent.
Conclusion: funding harvest on daily bars is closed as a profit engine. A006 forward test is cancelled (A005 amendment: FAIL closes the design).
It remains a possible regime switch: it would turn on if funding yields rise again, as in 2020-21.

### Why the harvest holdout failed: funding yields (annualised, paid to shorts; BTC / ETH / median of top-10 liquid coins)
2020: 17 / 27 / 24 | 2021: 31 / 38 / 41 | 2022: 4 / 1 / -1 | 2023: 8 / 8 / 7 | 2024: 12 / 13 / 14 | 2025: 5 / 5 / 4 | 2026 (to Oct): 3 / 2 / 2.
(Means across coins are distorted by outliers such as TRB at about -9% a day; medians are the reliable view.)
Gross harvest yield in the holdout year was roughly 2-5% before costs, so net of two-leg trading costs it is about zero and below cash.
The strategy only paid in 2020-21 and 2024. It would need funding yields well above ~10% to be worth running.
Pending: A003 (directional carry forward test, window 2026-11-22 to 2027-02-28). A006 cancelled.

## A007 order-flow / positioning signals (dev 2020-09-01 to 2025-10-31, 214 symbols, top-20 by volume): FAIL (near miss)
Net Sharpe per candidate: crowd_fade 1.50, taker_follow_3d 0.29, taker_fade_3d 0.09, toptrader_follow -0.08, oi_growth_fade -0.44, oi_growth_follow -0.60.
Best = crowd_fade (short coins where the 3-day mean of the all-account long/short ratio rose vs its 30-day mean; long where it fell): total return +1130%,
vol 36%, **max drawdown -35.5% (13 kill-switch halts)**, doubled-cost return still +669%, 5 of 6 blocks positive, deflated Sharpe prob **0.944** (N=6; mark is 0.95).
Failed marks: 2 (0.944 < 0.95) and 5 (drawdown 35.5% > 15%). Per protocol the family is closed and the holdout is NOT run for it.
Honest reading: first signal in this project with a large, cost-robust dev edge, but it is one winner among six, and its risk is too high at gross 1.0.
Data hygiene note: zero open interest treated as missing before the run (committed first; no returns were seen).
