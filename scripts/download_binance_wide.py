#!/usr/bin/env python3
"""Download EVERY Binance USDT-M perpetual (including delisted ones) from the public file index.

No hand-picked coin list, so no survivorship bias from the symbol list. No API key. Standard library only.
Only files that exist are requested (the index is read first), downloads run in parallel, each zip is
checksum-verified, and re-running skips files already downloaded.

    python scripts/download_binance_wide.py
    python scripts/download_binance_wide.py --start 2021-01 --workers 8
Output: data/raw_wide/ (same layout as download_binance.py)
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from download_binance import fetch  # noqa: E402  (checksum-verified, retrying download)

INDEX = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
FILES = "https://data.binance.vision"
BASE = "data/futures/um/monthly"
NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"
MONTH = re.compile(r"-(\d{4}-\d{2})\.zip$")


def parse_listing(xml_bytes: bytes):
    """Return (prefixes, keys, is_truncated, next_marker) from an S3 ListBucketResult document."""
    root = ET.fromstring(xml_bytes)
    prefixes = [e.findtext(NS + "Prefix") for e in root.findall(NS + "CommonPrefixes")]
    keys = [e.findtext(NS + "Key") for e in root.findall(NS + "Contents")]
    truncated = (root.findtext(NS + "IsTruncated") or "").lower() == "true"
    marker = root.findtext(NS + "NextMarker")
    return prefixes, keys, truncated, marker


def list_all(prefix: str, delimiter: bool = False):
    prefixes, keys, marker = [], [], ""
    while True:
        q = {"prefix": prefix, "max-keys": "1000"}
        if delimiter:
            q["delimiter"] = "/"
        if marker:
            q["marker"] = marker
        url = f"{INDEX}?{urllib.parse.urlencode(q)}"
        req = urllib.request.Request(url, headers={"User-Agent": "ariyan-crypto-ai/0.1"})
        with urllib.request.urlopen(req, timeout=60) as r:
            p, k, trunc, nxt = parse_listing(r.read())
        prefixes += p
        keys += k
        if not trunc:
            return prefixes, keys
        marker = nxt or (p[-1] if p else k[-1])


def usdt_symbols(kind: str) -> set[str]:
    prefixes, _ = list_all(f"{BASE}/{kind}/", delimiter=True)
    names = {p.rstrip("/").split("/")[-1] for p in prefixes}
    return {n for n in names if n.endswith("USDT") and "_" not in n}


def month_of(key: str) -> str | None:
    m = MONTH.search(key)
    return m.group(1) if m else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", default="2020-01", help="first month, YYYY-MM")
    ap.add_argument("--min-months", type=int, default=3, help="skip symbols with fewer months of data")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default="data/raw_wide")
    a = ap.parse_args()
    out = Path(a.out)

    print("Reading the public file index ...", flush=True)
    symbols = sorted(usdt_symbols("klines") & usdt_symbols("fundingRate"))
    print(f"{len(symbols)} USDT perpetuals have both prices and funding", flush=True)

    jobs = []  # (url, dest)
    kept = 0
    for i, sym in enumerate(symbols, 1):
        _, kk = list_all(f"{BASE}/klines/{sym}/1d/")
        _, fk = list_all(f"{BASE}/fundingRate/{sym}/")
        kk = [k for k in kk if k.endswith(".zip") and (month_of(k) or "") >= a.start]
        fk = [k for k in fk if k.endswith(".zip") and (month_of(k) or "") >= a.start]
        if len(kk) < a.min_months or not fk:
            continue
        kept += 1
        jobs += [(f"{FILES}/{k}", out / "klines" / sym / Path(k).name) for k in kk]
        jobs += [(f"{FILES}/{k}", out / "funding" / sym / Path(k).name) for k in fk]
        if i % 50 == 0:
            print(f"  indexed {i}/{len(symbols)} symbols", flush=True)
    print(f"{kept} symbols kept, {len(jobs)} files to fetch (already-downloaded files are skipped)", flush=True)

    counts = {"ok": 0, "cached": 0, "missing": 0, "failed": 0}
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(fetch, u, d) for u, d in jobs]
        for n, f in enumerate(as_completed(futs), 1):
            counts[f.result()] += 1
            if n % 500 == 0:
                print(f"  {n}/{len(jobs)} {counts}", flush=True)
    print(f"\nDone: {counts}")
    if counts["failed"]:
        print("Some files failed; run the same command again to retry them.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
