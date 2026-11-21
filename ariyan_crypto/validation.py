"""Honest-evaluation tools: Sharpe, probabilistic/deflated Sharpe, purged CV, walk-forward.

Sharpe inputs to PSR/DSR are PER-PERIOD (not annualised).
References: Bailey & Lopez de Prado (2014) deflated Sharpe ratio;
Lopez de Prado (2018) purged and embargoed cross-validation.
"""

from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np

_N = NormalDist()
EULER_GAMMA = 0.5772156649015329


def _clean(r) -> np.ndarray:
    a = np.asarray(r, dtype=float)
    return a[np.isfinite(a)]


def sharpe(r, periods_per_year: int = 1) -> float:
    a = _clean(r)
    if len(a) < 2:
        return 0.0
    sd = a.std(ddof=1)
    return 0.0 if sd == 0 else float(a.mean() / sd * math.sqrt(periods_per_year))


def _skew_kurt(a: np.ndarray) -> tuple[float, float]:
    s = a.std(ddof=0)
    if s == 0:
        return 0.0, 3.0
    z = (a - a.mean()) / s
    return float((z**3).mean()), float((z**4).mean())


def psr(r, sr_benchmark: float = 0.0) -> float:
    """Probability that the true per-period Sharpe exceeds `sr_benchmark`."""
    a = _clean(r)
    t = len(a)
    if t < 3:
        return 0.0
    sr = sharpe(a)
    skew, kurt = _skew_kurt(a)
    denom = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr**2
    if denom <= 0:
        return 0.0
    return _N.cdf((sr - sr_benchmark) * math.sqrt(t - 1) / math.sqrt(denom))


def expected_max_sharpe(n_trials: int, sr_variance: float) -> float:
    """Expected best per-period Sharpe among `n_trials` zero-skill trials."""
    if n_trials <= 1:
        return 0.0
    return math.sqrt(sr_variance) * (
        (1.0 - EULER_GAMMA) * _N.inv_cdf(1.0 - 1.0 / n_trials)
        + EULER_GAMMA * _N.inv_cdf(1.0 - 1.0 / (n_trials * math.e))
    )


def deflated_sharpe(r, n_trials: int, sr_variance: float | None = None) -> float:
    """PSR against the best-of-N luck threshold. Pass the TRUE number of trials you ran.

    If `sr_variance` (variance of Sharpe across your trials) is unknown, the
    sampling variance of a single Sharpe estimate is used as a rough proxy.
    """
    a = _clean(r)
    t = len(a)
    if t < 3:
        return 0.0
    if sr_variance is None:
        sr = sharpe(a)
        sr_variance = (1.0 + 0.5 * sr**2) / (t - 1)
    return psr(a, expected_max_sharpe(n_trials, sr_variance))


def purged_kfold(n: int, k: int = 5, horizon: int = 0, embargo: int = 0):
    """Yield (train_idx, test_idx). Train drops `horizon` bars before and
    `embargo` bars after each test block, so overlapping labels cannot leak."""
    if k < 2 or n < k:
        raise ValueError("need 2 <= k <= n")
    bounds = np.linspace(0, n, k + 1).astype(int)
    idx = np.arange(n)
    for a, b in zip(bounds[:-1], bounds[1:]):
        test = idx[a:b]
        keep = (idx < a - horizon) | (idx >= b + embargo)
        yield idx[keep], test


def walk_forward_splits(n: int, train_size: int, test_size: int, step: int | None = None):
    """Rolling walk-forward: train on the past window, test on the next unseen block."""
    step = step or test_size
    start = 0
    while start + train_size + test_size <= n:
        tr = np.arange(start, start + train_size)
        te = np.arange(start + train_size, start + train_size + test_size)
        yield tr, te
        start += step
