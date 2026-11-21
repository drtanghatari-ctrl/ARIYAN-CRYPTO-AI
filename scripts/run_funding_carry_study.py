#!/usr/bin/env python3
"""Run the A001 study exactly as pre-registered in docs/A001_FUNDING_CARRY_PROTOCOL.md.

    python scripts/run_funding_carry_study.py --panel data/panel          # development only
    python scripts/run_funding_carry_study.py --panel data/panel --holdout  # once, only if dev passed
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
from ariyan_crypto.signals import funding_carry_weights  # noqa: E402
from ariyan_crypto.validation import deflated_sharpe, sharpe  # noqa: E402

FAMILY = "a001_carry"
GRID = list(product((14, 30, 60), (0.2, 0.3)))  # 6 trials, fixed in the protocol
BASE = CostModel(0.00055, 0.0005)
STRESS = CostModel(0.0011, 0.0010)
RES = Path("results")


def load(panel: Path):
    close = pd.read_csv(panel / "close.csv", index_col=0, parse_dates=True)
    fund = pd.read_csv(panel / "funding.csv", index_col=0, parse_dates=True)
    return close, fund


def run(close, fund, lb, q, cost, start=None, end=None):
    w = funding_carry_weights(fund, lookback=lb, quantile=q)
    sl = slice(start, end)
    return run_backtest(close.loc[sl], w.loc[sl], fund.loc[sl], cost=cost)


def sr_variance(per_period_srs, t):
    proxy = 1.0 / (t - 1)
    return max(float(np.var(per_period_srs, ddof=1)), proxy) if len(per_period_srs) > 1 else proxy


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default="data/panel")
    ap.add_argument("--holdout", action="store_true")
    a = ap.parse_args()
    close, fund = load(Path(a.panel))
    RES.mkdir(exist_ok=True)
    reg = Registry(RES / "registry.jsonl")

    lock_path = RES / "holdout_lock.json"
    if lock_path.exists():
        hold_start = pd.Timestamp(json.loads(lock_path.read_text())["holdout_start"])
    else:
        hold_start = close.index.max() - pd.Timedelta(days=364)
        lock_path.write_text(json.dumps({"holdout_start": str(hold_start.date())}))
        reg.log_trial("disclosure", "holdout_locked", {"start": str(hold_start.date())}, {})
    dev_end = hold_start - pd.Timedelta(days=1)

    if a.holdout:
        rep_path = RES / "funding_carry_dev.json"
        if not rep_path.exists() or not json.loads(rep_path.read_text())["all_marks_pass"]:
            print("Refusing: development did not pass all marks.", file=sys.stderr)
            return 2
        if reg.n_trials("a001_holdout"):
            print("Refusing: holdout already used. The result is final.", file=sys.stderr)
            return 2
        best = json.loads(rep_path.read_text())["best"]
        res = run(close, fund, best["lookback"], best["quantile"], BASE, hold_start)
        m = metrics(res)
        reg.log_trial("a001_holdout", "holdout", best, m)
        print(json.dumps({"holdout": m, "params": best}, indent=2))
        return 0

    results = []
    for lb, q in GRID:
        res = run(close, fund, lb, q, BASE, end=dev_end)
        m = metrics(res)
        reg.log_trial(FAMILY, f"lb{lb}_q{q}", {"lookback": lb, "quantile": q}, m)
        results.append(((lb, q), res, m))
    best_params, best_res, best_m = max(results, key=lambda x: x[2]["sharpe"])
    r = best_res.returns.iloc[max(best_params[0], 1):]
    t = len(r)
    n_trials = reg.n_trials(FAMILY)
    srs = [sharpe(x[1].returns.iloc[max(best_params[0], 1):]) for x in results]
    dsr = deflated_sharpe(r, n_trials, sr_variance(srs, t))
    blocks = np.array_split(r.to_numpy(), 6)
    pos_blocks = int(sum(b.sum() > 0 for b in blocks))
    stress = metrics(run(close, fund, *best_params, STRESS, end=dev_end))

    marks = {
        "1_sharpe>=0.5": best_m["sharpe"] >= 0.5,
        "2_dsr>=0.95": dsr >= 0.95,
        "3_blocks>=4of6": pos_blocks >= 4,
        "4_doubled_cost_positive": stress["total_return"] > 0,
        "5_maxdd<=15%": best_m["max_drawdown"] >= -0.15,
    }
    report = {
        "dev_end": str(dev_end.date()),
        "n_trials_logged": n_trials,
        "all_trials": {f"lb{k[0]}_q{k[1]}": round(m["sharpe"], 3) for k, _, m in results},
        "best": {"lookback": best_params[0], "quantile": best_params[1]},
        "best_metrics": best_m,
        "deflated_sharpe_prob": dsr,
        "positive_blocks_of_6": pos_blocks,
        "doubled_cost_total_return": stress["total_return"],
        "marks": marks,
        "all_marks_pass": all(marks.values()),
    }
    (RES / "funding_carry_dev.json").write_text(json.dumps(report, indent=2, default=float))
    print(json.dumps(report, indent=2, default=float))
    print("\nVERDICT:", "PASS (holdout may be run once)" if report["all_marks_pass"] else "FAIL (family closed, no tuning)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
