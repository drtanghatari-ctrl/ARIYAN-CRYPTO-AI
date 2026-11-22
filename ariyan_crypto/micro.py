"""Order-flow / positioning / order-book data from the Binance public archive (USDT-M futures, daily zip files).

metrics  (5-minute rows, from 2020-09): create_time, symbol, sum_open_interest, sum_open_interest_value,
         count_toptrader_long_short_ratio, sum_toptrader_long_short_ratio, count_long_short_ratio,
         sum_taker_long_short_vol_ratio                         [header confirmed from Binance's issue tracker]
bookDepth (snapshots, from 2023-01): timestamp, percentage (-5..5 step 1), depth (base coin), notional (quote)
         Known problems: negative / off-price rows (mostly 2025-04..05, binance-public-data issue 431). The bid/ask sign of
         `percentage` is undocumented, so it is TESTED from implied prices (notional/depth) rather than assumed.

Every loader fails loudly on an unexpected header, and every daily value is aligned to the bar it was observed in:
the last 5-minute stamp of day D is 23:55, so day-D features are known at the day-D close (00:00 on D+1), the same
moment the daily close in close.csv becomes known.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

METRIC_COLS = [
    "sum_open_interest",
    "sum_open_interest_value",
    "count_toptrader_long_short_ratio",
    "sum_toptrader_long_short_ratio",
    "count_long_short_ratio",
    "sum_taker_long_short_vol_ratio",
]
DEPTH_COLS = ["timestamp", "percentage", "depth", "notional"]


def _read(path: str | Path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as z:
        with z.open(z.namelist()[0]) as f:
            return pd.read_csv(f)


def _ts(col: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(col):
        v = col.astype("int64")
        return pd.to_datetime(v.where(v < 10**14, v // 1000), unit="ms")
    return pd.to_datetime(col)


def parse_metrics(path: str | Path) -> pd.DataFrame:
    df = _read(path)
    need = {"create_time", *METRIC_COLS}
    if not need.issubset(df.columns):
        raise ValueError(f"unexpected metrics header {list(df.columns)} in {path}")
    out = df[METRIC_COLS].apply(pd.to_numeric, errors="coerce")
    out.index = _ts(df["create_time"])
    return out[~out.index.duplicated(keep="last")].sort_index()


def daily_metrics(m: pd.DataFrame) -> pd.DataFrame:
    """Daily features: levels at the day's last observation, ratios as the day's mean."""
    g = m.groupby(m.index.normalize())
    return pd.DataFrame(
        {
            "oi_qty": g["sum_open_interest"].last(),
            "oi_value": g["sum_open_interest_value"].last(),
            "top_ls": g["sum_toptrader_long_short_ratio"].mean(),
            "acct_ls": g["count_long_short_ratio"].mean(),
            "taker_ls": g["sum_taker_long_short_vol_ratio"].mean(),
        }
    )


def parse_bookdepth(path: str | Path) -> pd.DataFrame:
    df = _read(path)
    if not set(DEPTH_COLS).issubset(df.columns):
        raise ValueError(f"unexpected bookDepth header {list(df.columns)} in {path}")
    out = pd.DataFrame(
        {
            "ts": _ts(df["timestamp"]),
            "pct": pd.to_numeric(df["percentage"], errors="coerce").round(),
            "depth": pd.to_numeric(df["depth"], errors="coerce"),
            "notional": pd.to_numeric(df["notional"], errors="coerce"),
        }
    )
    bad = ~np.isfinite(out[["pct", "depth", "notional"]]).all(axis=1) | (out["depth"] <= 0) | (out["notional"] <= 0)
    out = out[~bad].copy()
    out["pct"] = out["pct"].astype(int)
    return out


def bookdepth_daily(book: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """One row per day: total depth within 1% and 5% (USD), bid-ask imbalance, plus self-checks.

    Imbalance assumes negative `percentage` = bid side. `sign_ok_frac` is the share of snapshots whose implied
    average price on the negative side (notional/depth at -5%) is below the positive side's, which is what that
    assumption predicts. Use imbalance only if it is close to 1.
    """
    empty = (pd.DataFrame(columns=["depth1_usd", "depth5_usd", "imb1", "imb5"], dtype=float), {"snapshots": 0})
    if book.empty:
        return empty
    b = book[book["pct"].abs().isin([1, 5])].copy()
    b["side"] = np.sign(b["pct"]).astype(int)
    b["lvl"] = b["pct"].abs()
    notion = b.pivot_table(index="ts", columns=["side", "lvl"], values="notional", aggfunc="first")
    depth = b.pivot_table(index="ts", columns=["side", "lvl"], values="depth", aggfunc="first")
    col = lambda p, s, l: p[(s, l)] if (s, l) in p.columns else pd.Series(np.nan, index=p.index)
    bid1, ask1, bid5, ask5 = (col(notion, -1, 1), col(notion, 1, 1), col(notion, -1, 5), col(notion, 1, 5))
    snap = pd.DataFrame(
        {
            "depth1_usd": bid1 + ask1,
            "depth5_usd": bid5 + ask5,
            "imb1": (bid1 - ask1) / (bid1 + ask1),
            "imb5": (bid5 - ask5) / (bid5 + ask5),
        }
    )
    imp_bid = col(notion, -1, 5) / col(depth, -1, 5)
    imp_ask = col(notion, 1, 5) / col(depth, 1, 5)
    ok = (imp_bid < imp_ask)[imp_bid.notna() & imp_ask.notna()]
    cum = (bid5 >= bid1)[bid5.notna() & bid1.notna()]
    qa = {
        "snapshots": int(len(snap)),
        "sign_ok_frac": float(ok.mean()) if len(ok) else None,
        "cumulative_frac": float(cum.mean()) if len(cum) else None,
    }
    return snap.groupby(snap.index.normalize()).median(), qa
