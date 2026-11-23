# A008: crowd_fade forward test (pre-registered; written before any forward data exists)

Why: A007 closed its family on a near miss (DSR 0.944, drawdown 35.5%). The development result cannot be re-used, and the
2025-11 to 2026-10 holdout stays unopened for this signal. The only clean evidence left is data that does not exist yet.

## Fixed now (no tuning)
Signal `crowd_fade` from `ariyan_crypto/flow.py`; eligible = top 20 by 30-day volume; `_long_short(quantile=0.3)`;
**gross = 0.5** (declared a priori to cut the 35% dev drawdown roughly in half; not optimised); base costs; daily.
Trials for deflation: 7 (A007's six plus this one).

## Window and data
2026-11-22 to the last full day available at evaluation. First evaluation no earlier than 2027-03-05 (re-download wide panel and
micro data; both downloaders are re-runnable). Same window as A003.

## Pass marks (all required)
1. Net return > 0 and net Sharpe > 0.5. 2. Max drawdown no deeper than 15%. 3. Positive with costs doubled.
4. At least 4 of 6 equal time blocks positive (or the window is too short, then 3 of 4 months).
5. Sign check: the long-minus-short leg difference before costs is positive.

## Consequence
PASS: paper trade on exchange testnet for 3 months, then consider tiny real size only with explicit human approval.
FAIL: crowd_fade is closed. Nothing here guarantees profit; ~100 days has low statistical power, so a PASS is only a gate.
