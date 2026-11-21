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
    funding: pd.DataFrame,
    lookback: int = 30,
    quantile: float = 0.25,
    gross: float = 1.0,
    eligible: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Dollar-neutral: long the lowest trailing funding, short the highest.

    Shorts earn funding when it is positive; longs pay it. Gross exposure is
    split equally between the long and short legs.
    """
    if not 0 < quantile <= 0.5:
        raise ValueError("quantile must be in (0, 0.5]")
    avg = funding.rolling(lookback, min_periods=lookback).mean()
    if eligible is not None:
        avg = avg.where(eligible.reindex_like(avg).fillna(False).astype(bool))
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


def top_n_by_volume(quote_volume: pd.DataFrame, n: int, lookback: int = 30) -> pd.DataFrame:
    """Boolean mask: the n most liquid assets by trailing mean USDT volume, known at each bar's close.

    This is the 'how many coins' dial. Fewer coins means lower costs per trade but less diversification.
    """
    liq = quote_volume.rolling(lookback, min_periods=lookback).mean()
    ranks = liq.rank(axis=1, ascending=False, method="first")
    return ranks <= n


def _long_short(score: pd.DataFrame, quantile: float, gross: float, eligible) -> pd.DataFrame:
    """Dollar-neutral: long the HIGHEST score, short the LOWEST; legs equal-weighted."""
    if not 0 < quantile <= 0.5:
        raise ValueError("quantile must be in (0, 0.5]")
    if eligible is not None:
        score = score.where(eligible.reindex_like(score).fillna(False).astype(bool))
    ranks = score.rank(axis=1, pct=True)
    longs = (ranks > 1.0 - quantile).astype(float)
    shorts = (ranks <= quantile).astype(float)
    long_w = longs.div(longs.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    short_w = shorts.div(shorts.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    return (long_w - short_w) * (gross / 2.0)


def reversal_weights(
    close: pd.DataFrame, lookback: int = 1, quantile: float = 0.3, gross: float = 1.0, eligible=None
) -> pd.DataFrame:
    """Short-term reversal: long recent losers, short recent winners.

    Evidence: daily reversal across 3,600+ coins, attributed to illiquidity; the few largest coins
    show daily momentum instead (Int. Rev. Financial Analysis, vol. 78, 2021). Expect the edge to live where costs are highest.
    """
    return _long_short(-close.pct_change(lookback), quantile, gross, eligible)


def xs_momentum_weights(
    close: pd.DataFrame, lookback: int = 28, quantile: float = 0.3, gross: float = 1.0, eligible=None
) -> pd.DataFrame:
    """Cross-sectional momentum: long past winners, short past losers (1-4 week lookbacks in the literature)."""
    return _long_short(close.pct_change(lookback), quantile, gross, eligible)
