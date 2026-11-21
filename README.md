# ARIYAN CRYPTO AI

Crypto-only research and paper-trading core. It exists to answer one question honestly:
**does a strategy have an edge after real costs?** It is not a profit machine, and nothing
here has been shown to be profitable yet.

## Why this repo exists
The earlier project (`ariyan-trading-ai-`) built rigorous machinery but tested forex/CFD
strategies through a swap-heavy broker, and every pre-registered test failed. Lessons carried over:

- Costs decide everything (fees, slippage, funding/financing).
- One backtest proves nothing; count every trial and deflate the Sharpe ratio.
- No result, no live money.

## What is here (v0.1)
| Module | Purpose |
|---|---|
| `backtest.py` | Perp backtester: no look-ahead, fees + slippage on turnover, directional funding, gross cap, drawdown kill switch |
| `validation.py` | Sharpe, probabilistic and deflated Sharpe, purged/embargoed k-fold, walk-forward splits |
| `signals.py` | Candidate signals: cross-sectional funding carry, time-series momentum |
| `registry.py` | Hash-chained trial log; its trial count feeds the deflated Sharpe |

## Rules
1. Pre-register the test (signal, parameters, pass marks) before looking at results.
2. Log every trial in the registry, including failures.
3. A candidate needs a deflated Sharpe probability of at least 0.95 on data it never saw.
4. Paper trade first. Live trading needs explicit human authorization, small size, and a tested kill switch.

## Run the tests
```
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

## Run the first real study (on your own computer)
Needs Python 3.10+ and internet. No API key, no account, no money involved.
```
git clone https://github.com/drtanghatari-ctrl/ARIYAN-CRYPTO-AI
cd ARIYAN-CRYPTO-AI
pip install -r requirements.txt
python scripts/download_binance.py      # public files from data.binance.vision, re-runnable
python scripts/build_panel.py           # makes data/ariyan_panel.zip (a few MB)
```
Then send `data/ariyan_panel.zip` to Claude, or run `python scripts/run_funding_carry_study.py` yourself.
The study follows `docs/A001_FUNDING_CARRY_PROTOCOL.md`, written before any result.

## Next
- Pre-registered study of cross-sectional funding carry on real data (protocol A001, ready).
- CCXT paper adapter (Bybit / OKX / Hyperliquid), then forward paper trading.

Not financial advice. Crypto derivatives can lose all capital.
