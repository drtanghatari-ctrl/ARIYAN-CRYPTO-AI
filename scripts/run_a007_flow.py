#!/usr/bin/env python3
"""Run A007 exactly as frozen in docs/A007_ORDER_FLOW_PROTOCOL.md (development only; single use).

    python scripts/run_a007_flow.py --panel data/panel_wide --micro data/micro_panel
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ariyan_crypto.backtest import CostModel, metrics, run_backtest  # noqa: E402
from ariyan_crypto.flow import flow_scores  # noqa: E402
from ariyan_crypto.registry import Registry  # noqa: E402
from ariyan_crypto.signals import _long_short, top_n_by_volume  # noqa: E402
from ariyan_crypto.validation import deflated_sharpe, sharpe  # noqa: E402

FAMILY = "a007_flow"
BASE, STRESS = CostModel(0.00055, 0.0005), CostModel(0.0011, 0.0010)
FEATS = ("oi_qty", "top_ls", "acct_ls", "taker_ls")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default="data/panel_wide")
    ap.add_argument("--micro", default="data/micro_panel")
    ap.add_argument("--results", default="results")
    a = ap.parse_args()
    res_dir = Path(a.results)
    rd = lambda d, n: pd.read_csv(Path(d) / n, index_col=0, parse_dates=True)
    close, fund, vol = (rd(a.panel, f"{n}.csv") for n in ("close", "funding", "volume"))
    micro = {f: rd(a.micro, f"{f}.csv") for f in FEATS}
    reg = Registry(res_dir / "registry.jsonl")
    if reg.n_trials(FAMILY):
        print("Refusing: A007 is a single pre-registered run and was already run.", file=sys.stderr)
        return 2
    dev_end = pd.Timestamp(json.loads((res_dir / "holdout_lock.json").read_text())["holdout_start"]) - pd.Timedelta(days=1)

    cols = [c for c in close.columns if all(c in m.columns for m in micro.values())]
    if len(cols) < 10:
        print(f"Refusing: only {len(cols)} symbols have all micro features.", file=sys.stderr)
        return 2
    start = max(m.dropna(how="all").index.min() for m in micro.values())
    idx = close.index[(close.index >= start) & (close.index <= dev_end)]
    c, f, v = close[cols].loc[idx], fund[cols].reindex(idx), vol[cols].loc[idx]
    micro = {k: m[cols].reindex(idx) for k, m in micro.items()}
    elig = top_n_by_volume(v, 20, 30)
    scores = flow_scores(micro)

    def run(name, cost):
        w = _long_short(scores[name], 0.3, 1.0, elig)
        return run_backtest(c, w, f, cost=cost)

    results = [(n, run(n, BASE)) for n in scores]
    ms = {n: metrics(r) for n, r in results}  # compute everything before logging
    best = max(ms, key=lambda n: ms[n]["sharpe"])
    best_res = dict(results)[best]
    r = best_res.returns.iloc[35:]
    srs = [sharpe(x.returns.iloc[35:]) for _, x in results]
    var = max(float(np.var(srs, ddof=1)), 1.0 / (len(r) - 1))
    dsr = deflated_sharpe(r, len(results), var)
    pos = int(sum(b.sum() > 0 for b in np.array_split(r.to_numpy(), 6)))
    dbl = metrics(run(best, STRESS))["total_return"]
    marks = {
        "1_sharpe>=0.5": ms[best]["sharpe"] >= 0.5,
        "2_dsr>=0.95": dsr >= 0.95,
        "3_blocks>=4of6": pos >= 4,
        "4_doubled_cost_positive": dbl > 0,
        "5_maxdd<=15%": ms[best]["max_drawdown"] >= -0.15,
    }
    report = {"symbols": len(cols), "start": str(idx.min().date()), "dev_end": str(dev_end.date()),
              "all_trials_sharpe": {n: round(ms[n]["sharpe"], 3) for n in ms}, "best": best,
              "best_metrics": ms[best], "dsr": dsr, "blocks_pos": pos, "doubled_cost_return": dbl,
              "marks": marks, "all_marks_pass": all(marks.values())}
    for n in ms:
        reg.log_trial(FAMILY, n, {"quantile": 0.3, "top_n": 20}, ms[n])
    (res_dir / "a007_flow_dev.json").write_text(json.dumps(report, indent=2, default=float))
    print(json.dumps(report, indent=2, default=float))
    print("\nVERDICT:", "PASS (holdout amendment next)" if report["all_marks_pass"] else "FAIL (family closed, no tuning)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
