"""Order-flow / positioning scores from daily micro panels. Each score is known at the day's close;
higher score = go long. Evidence status: NONE has passed a pre-registered test (see docs/A007)."""

from __future__ import annotations

import pandas as pd


def flow_scores(p: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """p holds daily panels: oi_qty, top_ls, acct_ls, taker_ls (columns = symbols). The six A007 candidates."""
    oi = p["oi_qty"].where(p["oi_qty"] > 0)  # zero open interest is a data glitch, not a signal
    return {
        "taker_follow_3d": p["taker_ls"].rolling(3, min_periods=3).mean(),
        "taker_fade_3d": -p["taker_ls"].rolling(3, min_periods=3).mean(),
        "toptrader_follow": p["top_ls"].rolling(3, min_periods=3).mean() - p["top_ls"].rolling(30, min_periods=30).mean(),
        "crowd_fade": -(p["acct_ls"].rolling(3, min_periods=3).mean() - p["acct_ls"].rolling(30, min_periods=30).mean()),
        "oi_growth_fade": -oi.pct_change(3, fill_method=None),
        "oi_growth_follow": oi.pct_change(3, fill_method=None),
    }
