# A005: Hedged funding harvest (long spot, short perpetual) - pre-registered protocol

Frozen 2026-11-22 before any spot data was seen. Reason for this design: a directional long-short basket
(A001/A004) has a Sharpe of 0.6 to 1.1, and with about 5.8 years of daily data a Sharpe near 1.5 is needed to reach
a deflated-Sharpe probability of 0.95. Only a low-volatility strategy can clear that bar honestly. Hedging price risk
away and collecting funding is the main candidate.

## Mechanism and conventions (see ariyan_crypto/harvest.py)
Per coin, long spot and short the USDT perp in equal notional. Return per unit notional per day = funding received
+ spot return - perp return. Total hedged notional <= 0.5 of equity (spot half + 100% margin on the perp leg), so
no liquidation is modelled or needed. Decision at close t earns day t+1.
Costs per unit of notional traded: spot 10 bp fee + 5 bp slippage, perp 5.5 bp fee + 5 bp slippage (both legs on every
entry and exit). Funding on missing days counts as 0.

## Data
Perp: the wide panel (859 USDT perps incl. delisted). Spot: Binance spot daily klines for every coin that has both.
Coins without a spot market (for example 1000PEPE-type contracts) are simply not tradable here.
Development period and locked holdout: identical to A001 (`results/holdout_lock.json`). The holdout is not used here.

## Candidates (4 trials, fixed now)
top_n in {10, 30} most liquid coins with spot  x  entry hurdle in {1 bp, 2 bp} per day of trailing 14-day mean funding.
Exit when trailing funding turns <= 0 (hysteresis). Total notional = 0.5 x min(1, coins_held / 5), equal split.

## Pass marks (best candidate by Sharpe; all required)
1. Net annualised Sharpe >= 1.0.
2. Deflated Sharpe probability >= 0.95 with N = 4 trials.
3. Positive net return in at least 4 of 6 equal time blocks.
4. Still net-positive with all costs doubled.
5. Max drawdown no deeper than 8%.
6. No calendar year with a net return below -3%.

## Outcome rules
PASS: forward paper trading on new data (same style as A003) before any thought of live money.
FAIL: harvest in this form is closed; record it and move on. The holdout stays locked either way.

## Known weaknesses stated in advance
Basis blow-ups on a daily close can be larger than a single day shows; exchange and counterparty risk are not modelled;
the 0.5 capital convention caps absolute returns at roughly half the funding yield; capacity falls in small coins.
