#!/usr/bin/env python3
"""Turn downloaded raw zips into one small panel (close.csv, funding.csv, qa.json) and a shareable zip.

    python scripts/build_panel.py
Then send `data/ariyan_panel.zip` (a few MB at most) back to Claude.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ariyan_crypto.data import build_panel, qa  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/raw")
    ap.add_argument("--out", default="data/panel")
    a = ap.parse_args()
    raw, out = Path(a.raw), Path(a.out)
    symbols = sorted(p.name for p in (raw / "klines").iterdir() if p.is_dir())
    if not symbols:
        print("No raw data found. Run scripts/download_binance.py first.", file=sys.stderr)
        return 1
    close, funding = build_panel(raw, symbols)
    out.mkdir(parents=True, exist_ok=True)
    close.to_csv(out / "close.csv", index_label="date")
    funding.to_csv(out / "funding.csv", index_label="date")
    report = qa(close, funding)
    (out / "qa.json").write_text(json.dumps(report, indent=2))
    zpath = out.parent / "ariyan_panel.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for name in ("close.csv", "funding.csv", "qa.json"):
            z.write(out / name, name)
    print(f"{len(symbols)} symbols, {close.index.min().date()} .. {close.index.max().date()}")
    for sym, r in report.items():
        flag = "  <-- check" if r["price_gaps"] or r["days_without_funding"] else ""
        print(f"{sym:10s} {r['first']} {r['days']:5d} days gaps={r['price_gaps']} no_funding={r['days_without_funding']}{flag}")
    print(f"\nSend this file to Claude: {zpath.resolve()} ({zpath.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
