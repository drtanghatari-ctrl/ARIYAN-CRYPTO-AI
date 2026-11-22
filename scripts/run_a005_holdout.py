#!/usr/bin/env python3
"""Single holdout run for the A005 candidate, per docs/A005_AMENDMENT_HOLDOUT.md."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ariyan_crypto.harvest import harvest_weights, hedged_returns, run_harvest  # noqa: E402
from ariyan_crypto.registry import Registry  # noqa: E402

RES = Path("results")
CASH_APY = 0.04


def window(net: pd.Series) -> dict:
    eq = (1 + net).cumprod()
    sd = net.std(ddof=1)
    return {"days": int(len(net)), "total_return": float(eq.iloc[-1] - 1),
            "max_drawdown": float((eq / eq.cummax() - 1).min()),
            "sharpe": float(net.mean() / sd * np.sqrt(365)) if sd > 0 else 0.0}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default="data/panel_wide")
    a = ap.parse_args()
    p = Path(a.panel)
    rd = lambda n: pd.read_csv(p / n, index_col=0, parse_dates=True)
    close, fund, vol, spot = rd("close.csv"), rd("funding.csv"), rd("volume.csv"), rd("spot_close.csv")
    reg = Registry(RES / "registry.jsonl")
    if reg.n_trials("a005_holdout"):
        print("Refusing: holdout already used. The result is final.", file=sys.stderr)
        return 2
    start = pd.Timestamp(json.loads((RES / "holdout_lock.json").read_text())["holdout_start"])
    end = close.index.max()
    spot = spot.reindex(close.index)
    rets = hedged_returns(spot, close, fund)
    w = harvest_weights(close, spot, fund, vol, 10, 0.0002)
    sl = slice(start - pd.Timedelta(days=1), end)
    base = run_harvest(w.loc[sl], rets.loc[sl], 1.0)["net"].loc[start:end]
    dbl = run_harvest(w.loc[sl], rets.loc[sl], 2.0)["net"].loc[start:end]
    b, d = window(base), window(dbl)
    cash = (1 + CASH_APY) ** (b["days"] / 365) - 1
    held = w.shift(1).fillna(0.0).loc[start:end]
    marks = {"1_return>0": b["total_return"] > 0, "2_maxdd<=3%": b["max_drawdown"] >= -0.03,
             "3_doubled_cost_return>0": d["total_return"] > 0, "4_beats_cash": b["total_return"] > cash}
    out = {"holdout": f"{start.date()}..{end.date()}", "result": b, "doubled_cost": d, "cash_benchmark_return": cash,
           "avg_coins_held": float((held > 0).sum(axis=1).mean()), "marks": marks, "all_marks_pass": all(marks.values())}
    reg.log_trial("a005_holdout", "top10_h0.0002", {"start": str(start.date()), "end": str(end.date())}, b)
    (RES / "a005_holdout.json").write_text(json.dumps(out, indent=2, default=float))
    print(json.dumps(out, indent=2, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())
