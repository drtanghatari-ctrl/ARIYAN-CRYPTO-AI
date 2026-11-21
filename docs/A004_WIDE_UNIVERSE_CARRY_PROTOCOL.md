# A004: Funding carry on the full Binance USDT-perp universe (pre-registered protocol)

Frozen before any wide-universe result. Purpose: remove the survivorship bias of the hand-picked 24-coin list in A001
and test whether the near-miss in A001 survives a broader, unbiased universe.

## Data
`scripts/download_binance_wide.py`: every USDT-M perpetual in the public index (including delisted), 2020-01 onward.
Panel built by `scripts/build_panel.py --raw data/raw_wide --out data/panel_wide`.
Development period and locked holdout: identical to A001 (`results/holdout_lock.json`). The holdout stays unused.

## Candidate (exactly one trial, fixed now)
`funding_carry_weights(lookback=14, quantile=0.3, gross=1.0)`, daily rebalance, eligible = the 50 most liquid
symbols by trailing 30-day USDT volume at each bar. No other parameter is tried.
(14 and 0.3 were chosen as the best of A001's six trials, so the cumulative trial count for this family is 7.)

## Execution and pass marks
Same as A001: 5.5 bp fee + 5 bp slippage per side, gross cap 2.0, 10% drawdown kill switch with 30-bar cooldown.
Pass marks 1 to 5 identical to A001, with deflated Sharpe computed against 7 cumulative trials.
Reported but not a mark: result using only the original 24 symbols, for comparison.

## Outcome rules
PASS: candidate proceeds to the A003 forward test (already scheduled either way). FAIL: carry on daily bars is closed.
Neither outcome unlocks the holdout or live trading.
