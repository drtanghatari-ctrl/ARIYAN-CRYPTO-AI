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
