import tempfile
import unittest
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from ariyan_crypto.micro import bookdepth_daily, daily_metrics, parse_bookdepth, parse_metrics

HEADER = ("create_time,symbol,sum_open_interest,sum_open_interest_value,count_toptrader_long_short_ratio,"
          "sum_toptrader_long_short_ratio,count_long_short_ratio,sum_taker_long_short_vol_ratio")


def write_zip(path, text):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("x.csv", text)


class MetricsTests(unittest.TestCase):
    def test_parse_and_daily_alignment(self):
        rows = [HEADER]
        for i, ts in enumerate(pd.date_range("2024-03-05 00:00", "2024-03-06 00:00", freq="5min")):
            rows.append(f"{ts:%Y-%m-%d %H:%M:%S},BTCUSDT,{100 + i},{1e6 + i},1.5,1.6,2.0,{1.0 if ts.day == 5 else 3.0}")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "m.zip"
            write_zip(p, "\n".join(rows))
            m = parse_metrics(p)
            self.assertEqual(len(m), 289)
            day = daily_metrics(m)
            self.assertEqual(list(day.index), [pd.Timestamp("2024-03-05"), pd.Timestamp("2024-03-06")])
            self.assertAlmostEqual(day.loc["2024-03-05", "oi_qty"], 100 + 287)  # last 5-min row of Mar 5 (23:55)
            self.assertAlmostEqual(day.loc["2024-03-05", "taker_ls"], 1.0)  # Mar 6 00:00 row belongs to Mar 6

    def test_bad_header_fails_loudly(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "m.zip"
            write_zip(p, "a,b,c\n1,2,3")
            with self.assertRaises(ValueError):
                parse_metrics(p)


def book_text(price=100.0, flip=False, junk=False):
    rows = ["timestamp,percentage,depth,notional"]
    for ts in ("2024-03-05 00:00:12", "2024-03-05 00:00:42"):
        for pct in (-5, -4, -3, -2, -1, 1, 2, 3, 4, 5):
            px = price * (1 + pct / 200.0)  # average price of the band: below mid for negatives
            if flip:
                px = price * (1 - pct / 200.0)
            depth = 10.0 * abs(pct) * (1.5 if pct < 0 else 1.0)  # bids deeper than asks, cumulative in |pct|
            rows.append(f"{ts},{pct},{depth},{depth * px}")
    if junk:
        rows.append("2024-03-05 00:00:12,-1,-5,-500")
    return "\n".join(rows)


class BookDepthTests(unittest.TestCase):
    def run_book(self, **kw):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "b.zip"
            write_zip(p, book_text(**kw))
            return bookdepth_daily(parse_bookdepth(p))

    def test_depth_imbalance_and_checks(self):
        day, qa = self.run_book()
        row = day.iloc[0]
        self.assertAlmostEqual(row["imb1"], (1.5 - 1.0) / 2.5, places=2)  # bids deeper
        self.assertGreater(row["depth5_usd"], row["depth1_usd"])
        self.assertEqual(qa["sign_ok_frac"], 1.0)
        self.assertEqual(qa["cumulative_frac"], 1.0)

    def test_sign_convention_violation_is_detected(self):
        _, qa = self.run_book(flip=True)
        self.assertEqual(qa["sign_ok_frac"], 0.0)

    def test_junk_rows_are_dropped(self):
        day, qa = self.run_book(junk=True)
        self.assertTrue(np.isfinite(day.iloc[0]["depth1_usd"]))
        self.assertEqual(qa["snapshots"], 2)


if __name__ == "__main__":
    unittest.main()


class FlowTests(unittest.TestCase):
    def test_flow_scores_use_only_past_and_have_six_candidates(self):
        import numpy as np
        import pandas as pd
        from ariyan_crypto.flow import flow_scores

        idx = pd.date_range("2024-01-01", periods=80, freq="D")
        rng = np.random.default_rng(0)
        p = {k: pd.DataFrame(1 + rng.random((80, 3)), index=idx, columns=list("ABC")) for k in ("oi_qty", "top_ls", "acct_ls", "taker_ls")}
        s = flow_scores(p)
        self.assertEqual(len(s), 6)
        p2 = {k: v.copy() for k, v in p.items()}
        p2["taker_ls"].iloc[-1] = 99.0  # change only the last day
        s2 = flow_scores(p2)
        for k in s:
            pd.testing.assert_frame_equal(s[k].iloc[:-1], s2[k].iloc[:-1])
