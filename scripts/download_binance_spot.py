#!/usr/bin/env python3
"""Download Binance SPOT daily klines for every coin that also has a perpetual in data/raw_wide.

Needed for the hedged funding harvest (long spot, short perp). Public files, no key, stdlib only,
checksum-verified, parallel, re-runnable.   python scripts/download_binance_spot.py
Output: data/raw_spot/klines/SYMBOL/*.zip
"""

from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from download_binance import fetch  # noqa: E402
from download_binance_wide import FILES, list_all, month_of  # noqa: E402

BASE = "data/spot/monthly/klines"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--perp-raw", default="data/raw_wide")
    ap.add_argument("--start", default="2020-01")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default="data/raw_spot")
    a = ap.parse_args()
    perp = {p.name for p in (Path(a.perp_raw) / "klines").iterdir() if p.is_dir()}
    if not perp:
        print("No perp data in", a.perp_raw, "- run download_binance_wide.py first.", file=sys.stderr)
        return 1
    prefixes, _ = list_all(f"{BASE}/", delimiter=True)
    spot = {p.rstrip("/").split("/")[-1] for p in prefixes}
    symbols = sorted(perp & spot)
    print(f"{len(symbols)} coins have both a perpetual and a spot market", flush=True)
    out, jobs = Path(a.out), []
    for i, sym in enumerate(symbols, 1):
        _, keys = list_all(f"{BASE}/{sym}/1d/")
        jobs += [(f"{FILES}/{k}", out / "klines" / sym / Path(k).name)
                 for k in keys if k.endswith(".zip") and (month_of(k) or "") >= a.start]
        if i % 50 == 0:
            print(f"  indexed {i}/{len(symbols)}", flush=True)
    print(f"{len(jobs)} files to fetch", flush=True)
    counts = {"ok": 0, "cached": 0, "missing": 0, "failed": 0}
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(fetch, u, d) for u, d in jobs]
        for n, f in enumerate(as_completed(futs), 1):
            counts[f.result()] += 1
            if n % 500 == 0:
                print(f"  {n}/{len(jobs)} {counts}", flush=True)
    print(f"\nDone: {counts}")
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
