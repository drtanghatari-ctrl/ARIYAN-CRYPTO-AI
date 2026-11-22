"""Hedged funding harvest: long spot + short perpetual, same notional, per coin.

Per unit of hedged notional held during day t:  funding_t + spot_return_t - perp_return_t
(shorts RECEIVE funding when it is positive). Price risk cancels except for the basis (spot minus perp).

Capital convention (conservative, no liquidation modelled): total hedged notional is at most 0.5 of equity,
so spot uses half the equity and the other half sits as 100% margin behind the short perp leg.
Decision at close of day t, position earns day t+1 (same no-look-ahead rule as backtest.py).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .signals import top_n_by_volume

SPOT_SIDE_COST = 0.0010 + 0.0005  # taker fee + slippage per unit traded
PERP_SIDE_COST = 0.00055 + 0.0005
COST_PER_UNIT_NOTIONAL = SPOT_SIDE_COST + PERP_SIDE_COST  # entering/exiting one unit of hedged notional touches both legs


def hedged_returns(spot: pd.DataFrame, perp: pd.DataFrame, funding: pd.DataFrame) -> pd.DataFrame:
    """Return per unit of hedged notional; NaN where either price is missing. Missing funding counts as 0."""
    sr = spot.pct_change(fill_method=None)
    pr = perp.pct_change(fill_method=None)
    return (funding.reindex_like(sr).fillna(0.0) + sr - pr).where(sr.notna() & pr.notna())


def harvest_weights(
    perp: pd.DataFrame,
    spot: pd.DataFrame,
    funding: pd.DataFrame,
    quote_volume: pd.DataFrame,
    top_n: int,
    enter_hurdle: float,
    lookback: int = 14,
    max_notional: float = 0.5,
    full_at: int = 5,
) -> pd.DataFrame:
    """Hysteresis rule: enter a coin when its trailing mean daily funding exceeds `enter_hurdle`,
    stay while it is still positive. Candidates are the `top_n` most liquid coins that have a spot market.
    Total notional is max_notional * min(1, held/full_at), split equally across held coins."""
    cols = [c for c in perp.columns if c in spot.columns]
    perp, spot = perp[cols], spot.reindex(perp.index)[cols]
    funding, vol = funding[cols], quote_volume[cols]
    trailing = funding.rolling(lookback, min_periods=lookback).mean()
    elig = (top_n_by_volume(vol.where(spot.notna()), top_n, 30) & spot.notna() & perp.notna()).to_numpy()
    tr = trailing.to_numpy()
    held = np.zeros_like(elig, dtype=bool)
    for t in range(len(perp)):
        prev = held[t - 1] if t else np.zeros(elig.shape[1], dtype=bool)
        enter = tr[t] > enter_hurdle
        stay = prev & (tr[t] > 0)
        held[t] = elig[t] & (np.nan_to_num(enter) | np.nan_to_num(stay)).astype(bool)
    k = held.sum(axis=1)
    total = max_notional * np.minimum(1.0, k / full_at)
    w = np.where(held, (total / np.maximum(k, 1))[:, None], 0.0)
    return pd.DataFrame(w, index=perp.index, columns=cols)


def run_harvest(weights: pd.DataFrame, rets: pd.DataFrame, cost_multiplier: float = 1.0) -> pd.DataFrame:
    """Daily net return series and diagnostics. weights[t] decided at close t, earns day t+1."""
    w = weights.shift(1).fillna(0.0)
    r = rets.reindex_like(w).fillna(0.0)
    gross = (w * r).sum(axis=1)
    turnover = w.diff().abs().sum(axis=1).fillna(w.abs().sum(axis=1))
    net = gross - turnover * COST_PER_UNIT_NOTIONAL * cost_multiplier
    return pd.DataFrame({"net": net, "gross": gross, "turnover": turnover, "invested": w.sum(axis=1)})
