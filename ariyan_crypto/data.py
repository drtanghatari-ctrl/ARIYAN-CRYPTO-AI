"""Load Binance USDT-M public archive files into aligned daily panels.

Alignment convention (matches backtest.py):
- A daily bar labelled D covers D 00:00 UTC to D+1 00:00 UTC; its close is known at D+1 00:00.
- A funding event stamped at (or a few ms after) D+1 00:00 settles the interval that
  ENDS at that close, so it belongs to day D. Events are summed per day.
- Funding is the fraction of notional paid by LONGS (negative: longs receive).
Missing data is reported by `qa`, never repaired silently.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


def _read_zip_csv(path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as z:
        with z.open(z.namelist()[0]) as f:
            df = pd.read_csv(f, header=None, dtype=str)
    if df.empty:
        return df
    if np.isnan(pd.to_numeric(df.iloc[0, 0], errors="coerce")):
        df = df.iloc[1:]  # header row present in newer files
    return df.reset_index(drop=True)


def _to_ms(col: pd.Series) -> pd.Series:
    v = pd.to_numeric(col).astype("int64")
    return v.where(v < 10**14, v // 1000)  # microsecond stamps -> ms


def load_klines_full(raw_dir: str | Path, symbol: str) -> pd.DataFrame:
    """Daily close and quote volume (USDT traded) indexed by UTC day."""
    files = sorted((Path(raw_dir) / "klines" / symbol).glob(f"{symbol}-1d-*.zip"))
    parts = []
    for p in files:
        df = _read_zip_csv(p)
        if len(df):
            ts = pd.to_datetime(_to_ms(df[0]), unit="ms")
            parts.append(
                pd.DataFrame(
                    {"close": pd.to_numeric(df[4]).to_numpy(), "quote_volume": pd.to_numeric(df[7]).to_numpy()},
                    index=ts.dt.normalize(),
                )
            )
    if not parts:
        return pd.DataFrame(columns=["close", "quote_volume"], dtype=float)
    out = pd.concat(parts)
    return out[~out.index.duplicated(keep="last")].sort_index()


def load_klines(raw_dir: str | Path, symbol: str) -> pd.Series:
    s = load_klines_full(raw_dir, symbol)["close"].astype(float)
    s.name = symbol
    return s


def load_funding(raw_dir: str | Path, symbol: str) -> pd.Series:
    files = sorted((Path(raw_dir) / "funding" / symbol).glob(f"{symbol}-fundingRate-*.zip"))
    parts = []
    for p in files:
        df = _read_zip_csv(p)
        if len(df):
            ts = pd.to_datetime(_to_ms(df[0]) - 60_000, unit="ms")  # event at D+1 00:00 -> day D
            parts.append(pd.Series(pd.to_numeric(df[2]).to_numpy(), index=ts))
    if not parts:
        return pd.Series(dtype=float, name=symbol)
    s = pd.concat(parts)
    s = s[~s.index.duplicated(keep="last")].sort_index()
    daily = s.groupby(s.index.normalize()).sum()
    daily.name = symbol
    return daily


def build_panel_full(raw_dir: str | Path, symbols: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Aligned daily (close, funding, quote_volume) panels; a missing day stays NaN."""
    closes, funds, vols = {}, {}, {}
    for sym in symbols:
        k = load_klines_full(raw_dir, sym)
        if len(k):
            closes[sym] = k["close"].astype(float)
            vols[sym] = k["quote_volume"].astype(float)
            funds[sym] = load_funding(raw_dir, sym)
    if not closes:
        raise ValueError("no kline data found")
    close = pd.DataFrame(closes).sort_index()
    full = pd.date_range(close.index.min(), close.index.max(), freq="D")
    close = close.reindex(full)
    funding = pd.DataFrame(funds).reindex(full)
    qvol = pd.DataFrame(vols).reindex(full)
    return close, funding, qvol


def build_panel(raw_dir: str | Path, symbols: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    close, funding, _ = build_panel_full(raw_dir, symbols)
    return close, funding


def qa(close: pd.DataFrame, funding: pd.DataFrame) -> dict:
    """Flag problems. Funding NaN where a price exists is reported (the backtest treats it as 0)."""
    report = {}
    for sym in close.columns:
        px = close[sym].dropna()
        if px.empty:
            continue
        window = close.loc[px.index.min() : px.index.max(), sym]
        no_fund = int((window.notna() & funding[sym].reindex(window.index).isna()).sum())
        report[sym] = {
            "first": str(px.index.min().date()),
            "last": str(px.index.max().date()),
            "days": int(px.size),
            "price_gaps": int(window.isna().sum()),
            "days_without_funding": no_fund,
            "max_abs_daily_return": float(px.pct_change().abs().max()),
        }
    return report
