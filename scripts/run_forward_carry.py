#!/usr/bin/env python3
"""Run A003 as frozen in docs/A003_FORWARD_TEST_PROTOCOL.md. Single use, only after the window has ended."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ariyan_crypto.backtest import CostModel, run_backtest  # noqa: E402
from ariyan_crypto.registry import Registry  # noqa: E402
from ariyan_crypto.signals import funding_carry_weights, top_n_by_volume  # noqa: E402

START, END = pd.Timestamp("2026-11-22"), pd.Timestamp("2027-02-28")
BASE, STRESS = CostModel(0.00055, 0.0005), CostModel(0.0011, 0.0010)
RES = Path("results")
ORIGINAL_24 = (
    "BTCUSDT ETHUSDT BNBUSDT XRPUSDT ADAUSDT LTCUSDT LINKUSDT TRXUSDT BCHUSDT ETCUSDT XLMUSDT XMRUSDT "
    "DASHUSDT ZECUSDT XTZUSDT ATOMUSDT NEOUSDT ONTUSDT IOTAUSDT BATUSDT VETUSDT QTUMUSDT ZILUSDT ENJUSDT"
).split()


def window_stats(returns: pd.Series) -> dict:
    r = returns.loc[START:END]
    eq = (1 + r).cumprod()
    sd = r.std(ddof=1)
    return {"days": int(len(r)), "total_return": float(eq.iloc[-1] - 1),
            "sharpe": float(r.mean() / sd * np.sqrt(365)) if sd > 0 else 0.0,
            "max_drawdown": float((eq / eq.cummax() - 1).min())}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default="data/panel_wide")
    a = ap.parse_args()
    p = Path(a.panel)
    rd = lambda n: pd.read_csv(p / n, index_col=0, parse_dates=True)
    close, fund, vol = rd("close.csv"), rd("funding.csv"), rd("volume.csv")
    if close.index.max() < END:
        print(f"Refusing: panel ends {close.index.max().date()}, window ends {END.date()}.", file=sys.stderr)
        return 2
    reg = Registry(RES / "registry.jsonl")
    if reg.n_trials("a003_forward"):
        print("Refusing: the forward test is single-use and was already run.", file=sys.stderr)
        return 2

    def run(cols, cost, top50):
        c, f, v = close[cols], fund[cols], vol[cols]
        elig = top_n_by_volume(v, 50, 30) if top50 else None
        w = funding_carry_weights(f, 14, 0.3, 1.0, eligible=elig)
        s = slice(START - pd.Timedelta(days=1), END)  # one prior bar so the first position is in force on day 1
        return run_backtest(c.loc[s], w.loc[s], f.loc[s], cost=cost).returns

    out = {}
    for name, cols, top50 in (("F1_original24", [c for c in ORIGINAL_24 if c in close.columns], False),
                              ("F2_wide_top50", list(close.columns), True)):
        base, dbl = window_stats(run(cols, BASE, top50)), window_stats(run(cols, STRESS, top50))
        marks = {"1_return>0": base["total_return"] > 0, "2_sharpe>=0.5": base["sharpe"] >= 0.5,
                 "3_maxdd<=15%": base["max_drawdown"] >= -0.15, "4_doubled_cost_return>0": dbl["total_return"] > 0}
        out[name] = {"base": base, "doubled_cost": dbl, "marks": marks, "pass": all(marks.values())}
        reg.log_trial("a003_forward", name, {"start": str(START.date()), "end": str(END.date())}, base)
    btc = close["BTCUSDT"].loc[START - pd.Timedelta(days=1):END]
    out["btc_buy_and_hold_return"] = float(btc.iloc[-1] / btc.iloc[0] - 1)
    (RES / "a003_forward.json").write_text(json.dumps(out, indent=2, default=float))
    print(json.dumps(out, indent=2, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())
