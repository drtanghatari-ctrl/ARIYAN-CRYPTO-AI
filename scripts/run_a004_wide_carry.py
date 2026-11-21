#!/usr/bin/env python3
"""Run A004 as frozen in docs/A004_WIDE_UNIVERSE_CARRY_PROTOCOL.md (development period only; one trial)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ariyan_crypto.backtest import CostModel, metrics, run_backtest  # noqa: E402
from ariyan_crypto.registry import Registry  # noqa: E402
from ariyan_crypto.signals import funding_carry_weights, top_n_by_volume  # noqa: E402
from ariyan_crypto.validation import deflated_sharpe  # noqa: E402

FAMILY = "a004_wide_carry"
BASE, STRESS = CostModel(0.00055, 0.0005), CostModel(0.0011, 0.0010)
RES = Path("results")
ORIGINAL_24 = (
    "BTCUSDT ETHUSDT BNBUSDT XRPUSDT ADAUSDT LTCUSDT LINKUSDT TRXUSDT BCHUSDT ETCUSDT XLMUSDT XMRUSDT "
    "DASHUSDT ZECUSDT XTZUSDT ATOMUSDT NEOUSDT ONTUSDT IOTAUSDT BATUSDT VETUSDT QTUMUSDT ZILUSDT ENJUSDT"
).split()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default="data/panel_wide")
    a = ap.parse_args()
    p = Path(a.panel)
    rd = lambda n: pd.read_csv(p / n, index_col=0, parse_dates=True)
    close, fund, vol = rd("close.csv"), rd("funding.csv"), rd("volume.csv")
    reg = Registry(RES / "registry.jsonl")
    if reg.n_trials(FAMILY):
        print("Refusing: A004 is a single pre-registered trial and was already run.", file=sys.stderr)
        return 2
    dev_end = pd.Timestamp(json.loads((RES / "holdout_lock.json").read_text())["holdout_start"]) - pd.Timedelta(days=1)

    def run(cols, cost):
        c, f, v = close[cols], fund[cols], vol[cols]
        w = funding_carry_weights(f, 14, 0.3, 1.0, eligible=top_n_by_volume(v, 50, 30))
        s = slice(None, dev_end)
        return run_backtest(c.loc[s], w.loc[s], f.loc[s], cost=cost)

    cols = list(close.columns)
    res = run(cols, BASE)
    m = metrics(res)
    reg.log_trial(FAMILY, "lb14_q0.3_top50", {"lookback": 14, "quantile": 0.3, "top_n": 50, "symbols": len(cols)}, m)

    a001 = [r["metrics"]["sharpe"] / np.sqrt(365) for r in reg.records("a001_carry")]
    n_trials = len(a001) + reg.n_trials(FAMILY)
    r = res.returns.iloc[45:]
    var = max(float(np.var(a001, ddof=1)) if len(a001) > 1 else 0.0, 1.0 / (len(r) - 1))
    dsr = deflated_sharpe(r, n_trials, var)
    pos = int(sum(b.sum() > 0 for b in np.array_split(r.to_numpy(), 6)))
    dbl = metrics(run(cols, STRESS))["total_return"]
    marks = {
        "1_sharpe>=0.5": m["sharpe"] >= 0.5,
        "2_dsr>=0.95": dsr >= 0.95,
        "3_blocks>=4of6": pos >= 4,
        "4_doubled_cost_positive": dbl > 0,
        "5_maxdd<=15%": m["max_drawdown"] >= -0.15,
    }
    orig = [c for c in ORIGINAL_24 if c in close.columns]
    info = metrics(run(orig, BASE)) if len(orig) >= 8 else None
    report = {"symbols_in_panel": len(cols), "dev_end": str(dev_end.date()), "n_trials_cumulative": n_trials,
              "metrics": m, "dsr": dsr, "blocks_pos": pos, "doubled_cost_return": dbl, "marks": marks,
              "all_marks_pass": all(marks.values()), "info_original24_metrics": info}
    (RES / "a004_wide_carry_dev.json").write_text(json.dumps(report, indent=2, default=float))
    print(json.dumps(report, indent=2, default=float))
    print("\nVERDICT:", "PASS (forward test A003 stays scheduled)" if report["all_marks_pass"] else "FAIL (carry on daily bars closed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
