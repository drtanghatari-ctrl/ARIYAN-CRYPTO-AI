#!/usr/bin/env python3
"""Run A002 exactly as frozen in docs/A002_REVERSAL_MOMENTUM_PROTOCOL.md (development period only).

    python scripts/run_reversal_momentum_study.py --panel data/panel
Holdout is NOT run by this script; it requires a pass and a separate, deliberate decision.
"""

from __future__ import annotations

import argparse
import json
import sys
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ariyan_crypto.backtest import CostModel, metrics, run_backtest  # noqa: E402
from ariyan_crypto.registry import Registry  # noqa: E402
from ariyan_crypto.signals import reversal_weights, top_n_by_volume, xs_momentum_weights  # noqa: E402
from ariyan_crypto.validation import deflated_sharpe, sharpe  # noqa: E402

FAMILY = "a002_revmom"
GRID = [("reversal", lb) for lb in (1, 3)] + [("momentum", lb) for lb in (14, 28)]
UNIVERSES = (6, 12, 24)
BASE, STRESS, TRIPLE = CostModel(0.00055, 0.0005), CostModel(0.0011, 0.0010), CostModel(0.00165, 0.0015)
RES = Path("results")


def weights(kind, lb, close, elig):
    fn = reversal_weights if kind == "reversal" else xs_momentum_weights
    return fn(close, lookback=lb, quantile=0.3, gross=1.0, eligible=elig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default="data/panel")
    a = ap.parse_args()
    p = Path(a.panel)
    rd = lambda n: pd.read_csv(p / n, index_col=0, parse_dates=True)
    close, fund, vol = rd("close.csv"), rd("funding.csv"), rd("volume.csv")
    lock = json.loads((RES / "holdout_lock.json").read_text())
    dev_end = pd.Timestamp(lock["holdout_start"]) - pd.Timedelta(days=1)
    reg = Registry(RES / "registry.jsonl")
    if reg.n_trials(FAMILY):
        print("Refusing: A002 already run; re-running would add undeclared trials.", file=sys.stderr)
        return 2

    def bt(kind, lb, n, cost):
        elig = top_n_by_volume(vol, n, 30)
        w = weights(kind, lb, close, elig)
        s = slice(None, dev_end)
        return run_backtest(close.loc[s], w.loc[s], fund.loc[s], cost=cost)

    trials = []
    for (kind, lb), n in product(GRID, UNIVERSES):
        res = bt(kind, lb, n, BASE)
        m = metrics(res)
        reg.log_trial(FAMILY, f"{kind}{lb}_N{n}", {"signal": kind, "lookback": lb, "universe": n}, m)
        trials.append({"kind": kind, "lb": lb, "n": n, "res": res, "m": m})

    skip = 31  # signal warm-up
    t_len = len(trials[0]["res"].returns.iloc[skip:])
    srs = [sharpe(t["res"].returns.iloc[skip:]) for t in trials]
    var = max(float(np.var(srs, ddof=1)), 1.0 / (t_len - 1))
    n_trials = reg.n_trials(FAMILY)

    def evaluate(t):
        r = t["res"].returns.iloc[skip:]
        dsr = deflated_sharpe(r, n_trials, var)
        pos = int(sum(b.sum() > 0 for b in np.array_split(r.to_numpy(), 6)))
        dbl = metrics(bt(t["kind"], t["lb"], t["n"], STRESS))["total_return"]
        marks = {
            "1_sharpe>=0.5": t["m"]["sharpe"] >= 0.5,
            "2_dsr>=0.95": dsr >= 0.95,
            "3_blocks>=4of6": pos >= 4,
            "4_doubled_cost_positive": dbl > 0,
            "5_maxdd<=15%": t["m"]["max_drawdown"] >= -0.15,
        }
        return {"name": f"{t['kind']}{t['lb']}_N{t['n']}", "sharpe": round(t["m"]["sharpe"], 3),
                "total_return": round(t["m"]["total_return"], 3), "max_dd": round(t["m"]["max_drawdown"], 3),
                "avg_turnover": round(t["m"]["avg_turnover"], 3), "dsr": round(dsr, 3),
                "blocks_pos": pos, "doubled_cost_return": round(dbl, 3),
                "triple_cost_return": round(metrics(bt(t["kind"], t["lb"], t["n"], TRIPLE))["total_return"], 3),
                "marks": marks, "pass": all(marks.values())}

    table = [evaluate(t) for t in trials]
    best = max(table, key=lambda r: r["sharpe"])
    report = {"dev_end": str(dev_end.date()), "n_trials": n_trials, "best_by_sharpe": best["name"],
              "any_pass": any(r["pass"] for r in table), "table": table}
    (RES / "reversal_momentum_dev.json").write_text(json.dumps(report, indent=2, default=float))
    print(f"{'trial':16s} {'Sharpe':>7s} {'ret':>7s} {'maxDD':>7s} {'turn':>6s} {'DSR':>6s} {'blk':>4s} {'2x ret':>7s} {'3x ret':>7s}  pass")
    for r in table:
        print(f"{r['name']:16s} {r['sharpe']:7.2f} {r['total_return']:7.2f} {r['max_dd']:7.2f} {r['avg_turnover']:6.2f} "
              f"{r['dsr']:6.2f} {r['blocks_pos']:4d} {r['doubled_cost_return']:7.2f} {r['triple_cost_return']:7.2f}  {r['pass']}")
    print("\nBest by Sharpe:", best["name"], "| any candidate passes all marks:", report["any_pass"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
