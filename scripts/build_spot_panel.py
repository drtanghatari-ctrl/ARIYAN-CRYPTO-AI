#!/usr/bin/env python3
"""Build the spot close panel aligned to the perp panel, and zip it for sharing.

    python scripts/build_spot_panel.py          -> data/ariyan_spot_close.zip (send to Claude)
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ariyan_crypto.data import load_klines  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/raw_spot")
    ap.add_argument("--panel", default="data/panel_wide")
    a = ap.parse_args()
    panel = Path(a.panel)
    index = pd.read_csv(panel / "close.csv", index_col=0, parse_dates=True).index
    syms = sorted(p.name for p in (Path(a.raw) / "klines").iterdir() if p.is_dir())
    cols = {s: load_klines(a.raw, s) for s in syms}
    spot = pd.DataFrame({s: v for s, v in cols.items() if len(v)}).reindex(index)
    spot.to_csv(panel / "spot_close.csv", index_label="date")
    z = panel.parent / "ariyan_spot_close.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(panel / "spot_close.csv", "spot_close.csv")
    print(f"{spot.shape[1]} spot symbols, {spot.index.min().date()} .. {spot.index.max().date()}")
    print(f"Send this file to Claude: {z.resolve()} ({z.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
