#!/usr/bin/env python3
"""Pick the coins worth downloading order-flow data for: the union of the K most liquid perps on ANY day.

Point-in-time by construction (a coin counts if it was top-K on some past day, including ones later delisted),
so the list is not biased toward today's survivors.   python scripts/select_micro_universe.py --k 15
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default="data/panel_wide")
    ap.add_argument("--k", type=int, default=15)
    ap.add_argument("--start", default="2020-09-01")
    ap.add_argument("--out", default="data/micro_universe.txt")
    a = ap.parse_args()
    vol = pd.read_csv(Path(a.panel) / "volume.csv", index_col=0, parse_dates=True).loc[a.start:]
    liq = vol.rolling(30, min_periods=30).mean()
    top = liq.rank(axis=1, ascending=False, method="first") <= a.k
    syms = sorted(top.columns[top.any()])
    Path(a.out).write_text("\n".join(syms) + "\n")
    print(f"{len(syms)} symbols were top-{a.k} by volume on at least one day -> {a.out}")
    print("Estimated metrics download: about", len(syms) * 2000 * 12 // 1000, "MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
