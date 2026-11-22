#!/usr/bin/env python3
"""Run A005 as frozen in docs/A005_HEDGED_HARVEST_PROTOCOL.md (development period only)."""

from __future__ import annotations

import argparse
import json
import sys
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ariyan_crypto.harvest import harvest_weights, hedged_returns, run_harvest  # noqa: E402
from ariyan_crypto.registry import Registry  # noqa: E402
from ariyan_crypto.validation import deflated_sharpe, sharpe  # noqa: E402

FAMILY = "a005_harvest"
GRID = list(product((10, 30), (0.0001, 0.0002)))
RES = Path("results")


def stats(net: pd.Series) -> dict:
    eq = (1 + net).cumprod()
    return {"sharpe": sharpe(net, 365), "total_return": float(eq.iloc[-1] - 1),
            "max_drawdown": float((eq / eq.cummax() - 1).min()),
            "ann_return": float(eq.iloc[-1] ** (365 / len(net)) - 1)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default="data/panel_wide")
    a = ap.parse_args()
    p = Path(a.panel)
    rd = lambda n: pd.read_csv(p / n, index_col=0, parse_dates=True)
    close, fund, vol, spot = rd("close.csv"), rd("funding.csv"), rd("volume.csv"), rd("spot_close.csv")
    reg = Registry(RES / "registry.jsonl")
    if reg.n_trials(FAMILY):
        print("Refusing: A005 already run; re-running would add undeclared trials.", file=sys.stderr)
        return 2
    dev_end = pd.Timestamp(json.loads((RES / "holdout_lock.json").read_text())["holdout_start"]) - pd.Timedelta(days=1)
    spot = spot.reindex(close.index)
    rets = hedged_returns(spot, close, fund)

    def run(top_n, hurdle, mult=1.0):
        w = harvest_weights(close, spot, fund, vol, top_n, hurdle)
        out = run_harvest(w.loc[:dev_end], rets.loc[:dev_end], mult)
        first = out.index[out["invested"] > 0][0]
        return out.loc[first:]

    runs = []
    for top_n, hurdle in GRID:
        out = run(top_n, hurdle)
        runs.append((top_n, hurdle, out, stats(out["net"])))
    srs = [sharpe(o["net"]) for _, _, o, _ in runs]
    best = max(runs, key=lambda x: x[3]["sharpe"])
    top_n, hurdle, out, s = best
    net = out["net"]
    var = max(float(np.var(srs, ddof=1)), 1.0 / (len(net) - 1))
    dsr = deflated_sharpe(net, len(GRID), var)
    blocks = int(sum(b.sum() > 0 for b in np.array_split(net.to_numpy(), 6)))
    dbl = stats(run(top_n, hurdle, 2.0)["net"])
    yearly = {int(y): float((1 + g).prod() - 1) for y, g in net.groupby(net.index.year)}
    marks = {"1_sharpe>=1.0": s["sharpe"] >= 1.0, "2_dsr>=0.95": dsr >= 0.95, "3_blocks>=4of6": blocks >= 4,
             "4_doubled_cost_positive": dbl["total_return"] > 0, "5_maxdd<=8%": s["max_drawdown"] >= -0.08,
             "6_no_year_below_-3%": min(yearly.values()) >= -0.03}
    report = {"dev_end": str(dev_end.date()), "first_invested": str(net.index[0].date()),
              "all_trials_sharpe": {f"top{t}_h{h}": round(st["sharpe"], 3) for t, h, _, st in runs},
              "best": {"top_n": top_n, "hurdle": hurdle}, "best_stats": s, "dsr": dsr, "blocks_pos": blocks,
              "doubled_cost": dbl, "yearly_returns": yearly, "avg_invested": float(out["invested"].mean()),
              "avg_daily_turnover": float(out["turnover"].mean()), "marks": marks, "all_marks_pass": all(marks.values())}
    for t, h, _, st in runs:  # log only after everything computed successfully
        reg.log_trial(FAMILY, f"top{t}_h{h}", {"top_n": t, "hurdle": h}, st)
    (RES / "a005_harvest_dev.json").write_text(json.dumps(report, indent=2, default=float))
    print(json.dumps(report, indent=2, default=float))
    print("\nVERDICT:", "PASS (forward paper test next)" if report["all_marks_pass"] else "FAIL (harvest in this form closed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
