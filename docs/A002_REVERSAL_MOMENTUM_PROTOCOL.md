# A002: Cross-sectional reversal and momentum by universe size (pre-registered protocol)

Frozen at commit time, before any real-data result. Run only after A001 has been run on the same panel.
Uses the same development period and the SAME locked holdout as A001 (`results/holdout_lock.json`).

## Question
After costs, do dollar-neutral reversal or momentum portfolios earn a positive return, and how does the result
change with the number of coins traded (ranked by trailing 30-day USDT volume)?

## Candidates (12 trials, fixed now)
- reversal, lookback in {1, 3} days
- cross-sectional momentum, lookback in {14, 28} days
- universe = top N by trailing 30-day mean quote volume, N in {6, 12, 24} (N=24 means all symbols)
- quantile 0.3 for every trial, gross 1.0, daily rebalance, long-short dollar neutral

## Execution model and pass marks
Identical to A001: costs 5.5 bp fee + 5 bp slippage per side, gross cap 2.0, 10% drawdown kill switch.
Marks on the best development candidate: net Sharpe >= 0.5; deflated Sharpe >= 0.95 with N = all trials
logged for A002; positive in >= 4 of 6 equal blocks; positive at doubled costs; max drawdown <= 15%.

## Breadth rule
Among passing candidates of the same signal, take the one with the smallest N. If net Sharpe falls as N grows,
the answer to "how many coins" is "no more than that N".

## Caveats
Slippage of 5 bp is optimistic for the smaller coins, so any reversal pass at N=24 gets a mandatory
3x-cost check before it is believed. Survivorship bias applies as in A001. One holdout run per family, final.
