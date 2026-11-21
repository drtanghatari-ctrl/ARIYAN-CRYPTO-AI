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
