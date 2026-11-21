# Strategy candidates (research notes, 2026-11-21)

Status of every row: **untested here**. Published numbers are gross, short-sample, or unreviewed; they are
reasons to test, not reasons to trade. Each one needs a pre-registered protocol and a pass before paper trading.

| # | Strategy | Evidence found | Main risk | Testable with free data? |
|---|---|---|---|---|
| 1 | Cross-sectional funding carry (A001) | ~0.4 net Sharpe out-of-sample in one study; plain funding-level carry has decayed | Crowding, survivorship | Yes (prices + funding) |
| 2 | Short-term reversal (1-3 day) | Strong across 3,600+ coins, but caused by illiquidity; the largest coins show momentum instead (Int. Rev. Fin. Analysis 78, 2021) | Edge sits in costly small coins | Yes (needs volume) |
| 3 | Cross-sectional momentum (1-4 week) | Significant in 2014-18 data (NBER w25882), but gross of costs, short sample, weak in equal-weight regressions | Momentum crashes, costs | Yes |
| 4 | Reversal + momentum blend | One GitHub backtest: net Sharpe ~2.5 walk-forward on 12 coins, hourly, 2.6 yrs; no live record, simplified costs | Probably overstated; small sample | Hourly data needed later |
| 5 | Pairs / cointegration | Paper reports beating buy-and-hold on BitMEX; no numbers or costs in the abstract | Microstructure, regime breaks | Later (hourly) |
| 6 | Systematic BTC covered calls | Filtered overlay +5% a year, Sharpe 0.20 to 0.30; unfiltered was negative over 2021-26 | Long-vol tail, bull runs | No (needs Deribit options data) |
| 7 | Time-series trend (tsmom) | Already in repo; your old project found trend rules failed in forex | Whipsaw | Yes |
| 8 | OI / liquidation-cascade fade | Plenty of commentary, no rigorous study found | Mostly anecdote | Needs open-interest data |

## Ranking (what to test first)
1. A001 funding carry (protocol written)
2. A002 reversal and momentum by liquidity tier (protocol written, runs after A001)
3. Blend of whatever survives 1 and 2
4. Hourly versions, pairs, then options income, only if daily results justify the data work

## "How many coins?" is a measurable trade-off, not a goal
- More coins give more diversification, but the extra coins are the illiquid ones. Reversal gets stronger there
  while fees, slippage and borrow cost rise, and capacity falls.
- So the number of coins is a parameter to optimise against NET results. A002 sweeps it (6, 12, 24 most liquid)
  and keeps the smallest set that passes. If the net edge shrinks as coins are added, we stop adding.
