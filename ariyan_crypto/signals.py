"""Signal candidates. Each returns target weights using only data up to bar t.

Evidence status (see README): NONE of these has passed a pre-registered test yet.
Cross-sectional funding carry is the first candidate because published research
finds a modest, cost-surviving out-of-sample edge (~0.4 Sharpe net); the plain
funding LEVEL trade has largely decayed. Do not expect more than that.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def funding_carry_weights(
    funding: pd.DataFrame, lookback: int = 30, quantile: float = 0.25, gross: float = 1.0
) -> pd.DataFrame:
    """Dollar-neutral: long the lowest trailing funding, short the highest.

    Shorts earn funding when it is positive; longs pay it. Gross exposure is
    split equally between the long and short legs.
    """
    if not 0 < quantile <= 0.5:
        raise ValueError("quantile must be in (0, 0.5]")
    avg = funding.rolling(lookback, min_periods=lookback).mean()
    ranks = avg.rank(axis=1, pct=True)
    longs = (ranks <= quantile).astype(float)
    shorts = (ranks > 1.0 - quantile).astype(float)
    long_w = longs.div(longs.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    short_w = shorts.div(shorts.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    return (long_w - short_w) * (gross / 2.0)


def tsmom_weights(
    close: pd.DataFrame,
    lookback: int = 90,
    vol_lookback: int = 30,
    asset_vol_target: float = 0.10,
    max_asset_scale: float = 3.0,
    periods_per_year: int = 365,
) -> pd.DataFrame:
    """Time-series momentum: sign of trailing return, scaled to equal risk per asset."""
    sign = np.sign(close.pct_change(lookback))
    vol = close.pct_change().rolling(vol_lookback, min_periods=vol_lookback).std() * np.sqrt(
        periods_per_year
    )
    scale = (asset_vol_target / vol).clip(upper=max_asset_scale)
    return (sign * scale / close.shape[1]).fillna(0.0)
