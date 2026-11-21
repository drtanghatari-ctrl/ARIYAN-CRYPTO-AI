# A001: Cross-sectional funding carry (pre-registered protocol)

Written BEFORE any result was seen. Changing anything below after the first run requires a new protocol
(A002) and counts as new trials.

## Question
Does a dollar-neutral portfolio that is long the lowest-funding and short the highest-funding USDT-M perps
earn a positive return after fees, slippage and funding, out of sample?

## Data
- Binance USDT-M daily klines and funding history from data.binance.vision, UTC, 2019-09 to the last full month.
- Universe: the fixed symbol list in `scripts/download_binance.py` (symbols join when listed).
- **Known bias:** the list was picked knowing these coins still exist, so survivorship bias flatters results.
  A pass is therefore weaker evidence than it looks; a fail is strong evidence.
- Missing funding on a priced day is treated as 0 and reported in `qa.json`.

## Split
- Holdout = the last 365 days of the panel, locked on first run in `results/holdout_lock.json`. Never viewed during development.
- Development = everything before it.

## Candidates (6 trials, fixed now)
`funding_carry_weights(lookback in {14, 30, 60}, quantile in {0.2, 0.3}, gross = 1.0)`, rebalanced daily.
No other parameters are tried. Every trial is logged in `results/registry.jsonl`.

## Execution model
Backtester defaults: taker fee 5.5 bp and slippage 5 bp per side on turnover, gross cap 2.0,
drawdown kill switch 10% with 30-bar cooldown, signal computed at close and earning the next bar.

## Pass marks (all required, on the best development candidate by Sharpe)
1. Net annualised Sharpe >= 0.5.
2. Deflated Sharpe probability >= 0.95 with N = cumulative trials logged for this family
   (variance of Sharpe across trials is the larger of the observed value and the single-estimate sampling variance).
3. Net-positive in at least 4 of 6 equal consecutive time blocks.
4. Still net-positive with fees and slippage doubled.
5. Maximum drawdown no deeper than 15%.

## Holdout
Run once, only if marks 1 to 5 all pass, on the single best candidate. The result is final.
FAIL on development: the family is closed; no tuning. Ideas for A002 must come from outside this data.

## What a pass would still not prove
Survivorship bias, exchange-specific funding, crowding (published carry has decayed), and capacity limits.
A pass only earns forward paper trading, never live money.
