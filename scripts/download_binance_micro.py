#!/usr/bin/env python3
"""Download order-flow (metrics) and optional order-book (bookDepth) daily files from data.binance.vision.

    python scripts/download_binance_micro.py --inspect          # FIRST: prints real file headers; paste them to Claude if a later step errors
    python scripts/download_binance_micro.py                    # metrics for data/micro_universe.txt (about 1 GB, 30-60 min)
    python scripts/download_binance_micro.py --kinds metrics bookDepth --depth-symbols BTCUSDT ETHUSDT --depth-start 2024-01
bookDepth files are large (about 0.5 MB per coin-day), so it is opt-in and limited to the symbols you list.
Stdlib only, checksum-verified, parallel, re-runnable.
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from download_binance import fetch  # noqa: E402
from download_binance_wide import FILES, list_all  # noqa: E402

DAILY = "data/futures/um/daily"
DAY = re.compile(r"-(\d{4}-\d{2}-\d{2})\.zip$")


def inspect(out: Path) -> int:
    for kind in ("metrics", "bookDepth"):
        key = f"{DAILY}/{kind}/BTCUSDT/BTCUSDT-{kind}-2024-03-05.zip"
        dest = out / "_inspect" / Path(key).name
        status = fetch(f"{FILES}/{key}", dest)
        print(f"\n== {kind}: {status}")
        if status in ("ok", "cached"):
            with zipfile.ZipFile(dest) as z:
                lines = z.read(z.namelist()[0]).decode().splitlines()
            print(f"{len(lines)} lines; first rows:")
            print("\n".join(lines[:6]))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inspect", action="store_true")
    ap.add_argument("--kinds", nargs="+", default=["metrics"], choices=["metrics", "bookDepth"])
    ap.add_argument("--universe", default="data/micro_universe.txt")
    ap.add_argument("--start", default="2020-09-01", help="metrics start date")
    ap.add_argument("--depth-symbols", nargs="+", default=["BTCUSDT", "ETHUSDT"])
    ap.add_argument("--depth-start", default="2023-01-01")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--out", default="data/raw_micro")
    a = ap.parse_args()
    out = Path(a.out)
    if a.inspect:
        return inspect(out)
    jobs = []
    for kind in a.kinds:
        if kind == "metrics":
            syms, start = [s for s in Path(a.universe).read_text().split() if s], a.start
        else:
            syms, start = a.depth_symbols, a.depth_start
        for i, sym in enumerate(syms, 1):
            _, keys = list_all(f"{DAILY}/{kind}/{sym}/")
            for k in keys:
                m = DAY.search(k)
                if m and m.group(1) >= start:
                    jobs.append((f"{FILES}/{k}", out / kind / sym / Path(k).name))
            if i % 10 == 0:
                print(f"  indexed {kind} {i}/{len(syms)}", flush=True)
    print(f"{len(jobs)} files to fetch (already-downloaded files are skipped)", flush=True)
    counts = {"ok": 0, "cached": 0, "missing": 0, "failed": 0}
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(fetch, u, d) for u, d in jobs]
        for n, f in enumerate(as_completed(futs), 1):
            counts[f.result()] += 1
            if n % 1000 == 0:
                print(f"  {n}/{len(jobs)} {counts}", flush=True)
    print(f"\nDone: {counts}")
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
