#!/usr/bin/env python3
"""Download Binance USDT-M futures DAILY klines and FUNDING history (public files, no API key).

Source: https://data.binance.vision  (monthly zip files, each checked against its .CHECKSUM)
Standard library only. Safe to re-run: existing verified files are skipped.

    python scripts/download_binance.py
    python scripts/download_binance.py --symbols BTCUSDT ETHUSDT --start 2022-01
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

BASE = "https://data.binance.vision/data/futures/um/monthly"

# Fixed list of long-history perps. Chosen with hindsight about which still trade, so the
# study carries survivorship bias; the protocol states this. Symbols with no files are skipped.
DEFAULT_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "LTCUSDT", "LINKUSDT", "TRXUSDT",
    "BCHUSDT", "ETCUSDT", "XLMUSDT", "XMRUSDT", "DASHUSDT", "ZECUSDT", "XTZUSDT", "ATOMUSDT",
    "NEOUSDT", "ONTUSDT", "IOTAUSDT", "BATUSDT", "VETUSDT", "QTUMUSDT", "ZILUSDT", "ENJUSDT",
]


def month_range(start: str, end: str):
    y, m = map(int, start.split("-"))
    ye, me = map(int, end.split("-"))
    while (y, m) <= (ye, me):
        yield f"{y:04d}-{m:02d}"
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def previous_month() -> str:
    t = date.today()
    y, m = (t.year - 1, 12) if t.month == 1 else (t.year, t.month - 1)
    return f"{y:04d}-{m:02d}"


def _get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "ariyan-crypto-ai/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch(url: str, dest: Path, tries: int = 4) -> str:
    """Return 'ok', 'cached', 'missing' (404) or 'failed'. Verifies the SHA-256 checksum."""
    if dest.exists() and dest.stat().st_size > 0:
        return "cached"
    for attempt in range(tries):
        try:
            data = _get(url)
            try:
                expected = _get(url + ".CHECKSUM").split()[0].decode()
                if hashlib.sha256(data).hexdigest() != expected:
                    raise ValueError("checksum mismatch")
            except urllib.error.HTTPError as e:
                if e.code != 404:
                    raise  # no checksum file published: accept the zip
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            return "ok"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return "missing"
            err = f"HTTP {e.code}"
        except Exception as e:  # network trouble, checksum mismatch
            err = f"{type(e).__name__}: {e}"
        time.sleep(2 * (attempt + 1))
    print(f"  FAILED {url} ({err})", file=sys.stderr)
    return "failed"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbols", nargs="+", default=DEFAULT_SYMBOLS)
    ap.add_argument("--start", default="2019-09", help="first month, YYYY-MM")
    ap.add_argument("--end", default=previous_month(), help="last month, YYYY-MM (default: last full month)")
    ap.add_argument("--out", default="data/raw")
    a = ap.parse_args()
    out = Path(a.out)
    failed = 0
    for sym in a.symbols:
        counts = {"ok": 0, "cached": 0, "missing": 0, "failed": 0}
        for ym in month_range(a.start, a.end):
            for kind, name in (("klines", f"{sym}-1d-{ym}"), ("fundingRate", f"{sym}-fundingRate-{ym}")):
                sub = "klines" if kind == "klines" else "funding"
                url = f"{BASE}/{kind}/{sym}/" + ("1d/" if kind == "klines" else "") + f"{name}.zip"
                counts[fetch(url, out / sub / sym / f"{name}.zip")] += 1
        failed += counts["failed"]
        print(f"{sym}: {counts}", flush=True)
    print("\nDone. 'missing' months are normal before a symbol was listed.")
    if failed:
        print(f"{failed} files failed; re-run the same command to retry them.", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
