"""Cost-aware backtester for crypto perpetual futures.

Conventions (read these before trusting any number):
- Weights are fractions of equity per asset (positive long, negative short).
- A weight computed from data up to the close of bar t-1 is held during bar t
  and earns the return of bar t. Nothing computed at bar t can earn bar t.
- Trades execute at the close of the signal bar; slippage + fees are charged on
  turnover to approximate that fill.
- `funding[t, i]` is the fraction of notional paid by LONGS during bar t
  (negative means longs receive). Shorts receive what longs pay.
- A drawdown kill switch flattens the book and stays flat for `cooldown` bars.
- Liquidation is not modelled: keep `max_gross` low and treat results as upper bounds.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CostModel:
    """Per-side proportional costs charged on turnover (fractions of notional)."""

    taker_fee: float = 0.00055
    slippage: float = 0.0005

    def per_unit_turnover(self) -> float:
        return self.taker_fee + self.slippage


@dataclass
class BacktestResult:
    returns: pd.Series  # per-bar portfolio return after costs and funding
    turnover: pd.Series  # sum of |delta weight| per bar
    equity: pd.Series
    halts: int  # number of kill-switch activations
    ruined: bool


def run_backtest(
    close: pd.DataFrame,
    weights: pd.DataFrame,
    funding: pd.DataFrame | None = None,
    cost: CostModel = CostModel(),
    max_gross: float = 2.0,
    max_drawdown: float = 0.10,
    cooldown: int = 30,
) -> BacktestResult:
    idx, cols = close.index, close.columns
    ret = close.pct_change().fillna(0.0).to_numpy(dtype=float)
    w_all = (
        weights.reindex(index=idx, columns=cols).fillna(0.0).shift(1).fillna(0.0).to_numpy(dtype=float)
    )
    if funding is None:
        fund = np.zeros_like(ret)
    else:
        fund = funding.reindex(index=idx, columns=cols).fillna(0.0).to_numpy(dtype=float)

    n_bars, n_assets = ret.shape
    prev = np.zeros(n_assets)
    equity, peak = 1.0, 1.0
    halted_until = -1
    halts = 0
    ruined = False
    pnl_out = np.zeros(n_bars)
    turn_out = np.zeros(n_bars)
    eq_out = np.ones(n_bars)
    unit_cost = cost.per_unit_turnover()

    for t in range(n_bars):
        if ruined:
            eq_out[t] = equity
            continue
        w = w_all[t].copy()
        gross = np.abs(w).sum()
        if gross > max_gross:
            w *= max_gross / gross
        if t <= halted_until:
            w[:] = 0.0
        if t == halted_until + 1 and halted_until >= 0:
            peak = equity  # fresh high-water mark after the cooldown
        turnover = np.abs(w - prev).sum()
        pnl = float(w @ ret[t]) - float(w @ fund[t]) - turnover * unit_cost
        equity *= 1.0 + pnl
        pnl_out[t], turn_out[t], eq_out[t] = pnl, turnover, equity
        prev = w
        if equity <= 0.0:
            ruined = True
            continue
        peak = max(peak, equity)
        if t > halted_until and equity / peak - 1.0 < -max_drawdown:
            halted_until = t + cooldown
            halts += 1

    return BacktestResult(
        returns=pd.Series(pnl_out, index=idx, name="returns"),
        turnover=pd.Series(turn_out, index=idx, name="turnover"),
        equity=pd.Series(eq_out, index=idx, name="equity"),
        halts=halts,
        ruined=ruined,
    )


def metrics(result: BacktestResult, periods_per_year: int = 365) -> dict:
    r = result.returns.to_numpy()
    sd = r.std(ddof=1) if len(r) > 1 else 0.0
    eq = result.equity.to_numpy()
    dd = eq / np.maximum.accumulate(eq) - 1.0
    return {
        "total_return": float(eq[-1] - 1.0),
        "ann_vol": float(sd * np.sqrt(periods_per_year)),
        "sharpe": float(r.mean() / sd * np.sqrt(periods_per_year)) if sd > 0 else 0.0,
        "max_drawdown": float(dd.min()),
        "avg_turnover": float(result.turnover.mean()),
        "halts": result.halts,
        "ruined": result.ruined,
    }
