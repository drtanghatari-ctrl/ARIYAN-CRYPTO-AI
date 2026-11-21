import tempfile
import unittest
import zipfile
from pathlib import Path

import pandas as pd

from ariyan_crypto.data import build_panel, load_funding, load_klines, qa

DAY = 86_400_000


def ms(date_str, extra=0):
    return int(pd.Timestamp(date_str).timestamp() * 1000) + extra


def write_zip(path: Path, csv_text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(path.stem + ".csv", csv_text)


class DataTests(unittest.TestCase):
    def test_klines_header_and_microsecond_stamps(self):
        with tempfile.TemporaryDirectory() as d:
            raw = Path(d)
            rows = "\n".join(f"{ms('2024-01-0%d' % i)},1,1,1,{100 + i},1,0,0,0,0,0,0" for i in (1, 2))
            write_zip(raw / "klines/AAAUSDT/AAAUSDT-1d-2024-01.zip",
                      "open_time,open,high,low,close,volume,close_time,qv,n,tb,tq,ignore\n" + rows)
            us = f"{ms('2024-02-01') * 1000},1,1,1,200,1,0,0,0,0,0,0"
            write_zip(raw / "klines/AAAUSDT/AAAUSDT-1d-2024-02.zip", us)
            s = load_klines(raw, "AAAUSDT")
            self.assertEqual(list(s.values), [101, 102, 200])
            self.assertEqual(s.index[-1], pd.Timestamp("2024-02-01"))

    def test_funding_events_map_to_the_day_they_settle(self):
        with tempfile.TemporaryDirectory() as d:
            raw = Path(d)
            ev = [
                (ms("2024-01-01", 8 * 3600_000 + 7), 0.0001),
                (ms("2024-01-01", 16 * 3600_000 + 4), 0.0002),
                (ms("2024-01-02", 5), 0.0004),  # 00:00 on Jan 2 closes Jan 1
                (ms("2024-01-02", 8 * 3600_000 + 3), 0.0008),
            ]
            csv = "calc_time,funding_interval_hours,last_funding_rate\n" + "\n".join(
                f"{t},8,{r}" for t, r in ev
            )
            write_zip(raw / "funding/AAAUSDT/AAAUSDT-fundingRate-2024-01.zip", csv)
            s = load_funding(raw, "AAAUSDT")
            self.assertAlmostEqual(s[pd.Timestamp("2024-01-01")], 0.0007)
            self.assertAlmostEqual(s[pd.Timestamp("2024-01-02")], 0.0008)

    def test_panel_and_qa_flag_gaps(self):
        with tempfile.TemporaryDirectory() as d:
            raw = Path(d)
            rows = "\n".join(f"{ms('2024-01-%02d' % i)},1,1,1,{100 + i},1,0,0,0,0,0,0" for i in (1, 2, 4))
            write_zip(raw / "klines/AAAUSDT/AAAUSDT-1d-2024-01.zip", rows)
            close, funding = build_panel(raw, ["AAAUSDT", "MISSINGUSDT"])
            self.assertEqual(list(close.columns), ["AAAUSDT"])
            self.assertEqual(len(close), 4)  # Jan 3 present as NaN
            rep = qa(close, funding)["AAAUSDT"]
            self.assertEqual(rep["price_gaps"], 1)
            self.assertEqual(rep["days_without_funding"], 3)


if __name__ == "__main__":
    unittest.main()
