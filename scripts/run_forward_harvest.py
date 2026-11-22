#!/usr/bin/env python3
"""Run A006 as frozen in docs/A006_HARVEST_FORWARD_TEST_PROTOCOL.md. Single use, only after the window has ended."""

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

START, END = pd.Timestamp("2026-11-22"), pd.Timestamp("2027-02-28")
CASH_APY = 0.04
RES = Path("results")


def window(net: pd.Series) -> dict:
    r = net.loc[START:END]
    eq = (1 + r).cumprod()
    sd = r.std(ddof=1)
    return {"days": int(len(r)), "total_return": float(eq.iloc[-1] - 1),
            "max_drawdown": float((eq / eq.cummax() - 1).min()),
            "sharpe": float(r.mean() / sd * np.sqrt(365)) if sd > 0 else 0.0}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default="data/panel_wide")
    a = ap.parse_args()
    p = Path(a.panel)
    rd = lambda n: pd.read_csv(p / n, index_col=0, parse_dates=True)
    close, fund, vol, spot = rd("close.csv"), rd("funding.csv"), rd("volume.csv"), rd("spot_close.csv")
    if close.index.max() < END or spot.dropna(how="all").index.max() < END:
        print(f"Refusing: panels must reach {END.date()}.", file=sys.stderr)
        return 2
    reg = Registry(RES / "registry.jsonl")
    if reg.n_trials("a006_forward_harvest"):
        print("Refusing: single-use forward test already run.", file=sys.stderr)
        return 2
    spot = spot.reindex(close.index)
    rets = hedged_returns(spot, close, fund)
    w = harvest_weights(close, spot, fund, vol, 10, 0.0002)
    sl = slice(START - pd.Timedelta(days=1), END)
    base = run_harvest(w.loc[sl], rets.loc[sl], 1.0)
    dbl = run_harvest(w.loc[sl], rets.loc[sl], 2.0)
    b, d = window(base["net"]), window(dbl["net"])
    cash = (1 + CASH_APY) ** (b["days"] / 365) - 1
    gross_w = w.shift(1).fillna(0.0).loc[START:END]
    marks = {"1_return>0": b["total_return"] > 0, "2_maxdd<=3%": b["max_drawdown"] >= -0.03,
             "3_doubled_cost_return>0": d["total_return"] > 0, "4_beats_cash": b["total_return"] > cash}
    out = {"window": b, "doubled_cost": d, "cash_benchmark_return": cash,
           "avg_coins_held": float((gross_w > 0).sum(axis=1).mean()), "avg_invested": float(gross_w.sum(axis=1).mean()),
           "marks": marks, "all_marks_pass": all(marks.values())}
    reg.log_trial("a006_forward_harvest", "top10_h0.0002", {"start": str(START.date()), "end": str(END.date())}, b)
    (RES / "a006_forward_harvest.json").write_text(json.dumps(out, indent=2, default=float))
    print(json.dumps(out, indent=2, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())
