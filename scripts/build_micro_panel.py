#!/usr/bin/env python3
"""Turn raw metrics / bookDepth zips into daily panels (one CSV per feature) and a shareable zip.

    python scripts/build_micro_panel.py   ->  data/ariyan_micro_panel.zip  (send to Claude)
Files that fail to parse are counted and reported, never silently skipped.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ariyan_crypto.micro import bookdepth_daily, daily_metrics, parse_bookdepth, parse_metrics  # noqa: E402


def collect(raw: Path, kind: str, parse, daily):
    frames, qa, errors = {}, {}, {}
    for sdir in sorted(p for p in (raw / kind).glob("*") if p.is_dir() and not p.name.startswith("_")):
        parts, bad, sq = [], 0, []
        for f in sorted(sdir.glob("*.zip")):
            try:
                res = daily(parse(f))
            except Exception as e:  # noqa: BLE001
                bad += 1
                errors.setdefault(sdir.name, str(e)[:160])
                continue
            if isinstance(res, tuple):
                res, q = res
                sq.append(q)
            parts.append(res)
        if parts:
            d = pd.concat(parts)
            frames[sdir.name] = d[~d.index.duplicated(keep="last")].sort_index()
        qa[sdir.name] = {"files_ok": len(parts), "files_failed": bad}
        if sq:
            vals = [q["sign_ok_frac"] for q in sq if q.get("sign_ok_frac") is not None]
            cums = [q["cumulative_frac"] for q in sq if q.get("cumulative_frac") is not None]
            qa[sdir.name]["sign_ok_frac_mean"] = float(sum(vals) / len(vals)) if vals else None
            qa[sdir.name]["cumulative_frac_mean"] = float(sum(cums) / len(cums)) if cums else None
    return frames, qa, errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/raw_micro")
    ap.add_argument("--out", default="data/micro_panel")
    a = ap.parse_args()
    raw, out = Path(a.raw), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    report, panels = {}, {}
    if (raw / "metrics").exists():
        fr, qa, err = collect(raw, "metrics", parse_metrics, daily_metrics)
        report["metrics"], report["metrics_errors"] = qa, err
        for feat in ("oi_qty", "oi_value", "top_ls", "acct_ls", "taker_ls"):
            panels[feat] = pd.DataFrame({s: d[feat] for s, d in fr.items()}).sort_index()
    if (raw / "bookDepth").exists():
        fr, qa, err = collect(raw, "bookDepth", parse_bookdepth, bookdepth_daily)
        report["bookDepth"], report["bookDepth_errors"] = qa, err
        for feat in ("depth1_usd", "depth5_usd", "imb1", "imb5"):
            panels[feat] = pd.DataFrame({s: d[feat] for s, d in fr.items()}).sort_index()
    if not panels:
        print("No raw micro data found. Run scripts/download_binance_micro.py first.", file=sys.stderr)
        return 1
    z = out.parent / f"ariyan_{out.name}.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, df in panels.items():
            df.to_csv(out / f"{name}.csv", index_label="date")
            zf.write(out / f"{name}.csv", f"{name}.csv")
        (out / "qa.json").write_text(json.dumps(report, indent=2))
        zf.write(out / "qa.json", "qa.json")
    for name, df in panels.items():
        print(f"{name:11s} {df.shape[1]:3d} symbols  {df.index.min().date()} .. {df.index.max().date()}")
    failed = sum(v["files_failed"] for k in ("metrics", "bookDepth") for v in report.get(k, {}).values())
    print(f"files that failed to parse: {failed}")
    for k in ("metrics_errors", "bookDepth_errors"):
        for sym, msg in list(report.get(k, {}).items())[:3]:
            print(f"  {k} {sym}: {msg}")
    for sym, q in report.get("bookDepth", {}).items():
        print(f"  bookDepth {sym}: sign_ok={q.get('sign_ok_frac_mean')} cumulative={q.get('cumulative_frac_mean')}")
    print(f"\nSend this file to Claude: {z.resolve()} ({z.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
