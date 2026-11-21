import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from ariyan_crypto.registry import Registry
from ariyan_crypto.signals import funding_carry_weights, tsmom_weights


def idx(n):
    return pd.date_range("2024-01-01", periods=n, freq="D")


class SignalTests(unittest.TestCase):
    def test_funding_carry_is_dollar_neutral_and_picks_extremes(self):
        f = pd.DataFrame(
            {"A": [0.004] * 40, "B": [0.003] * 40, "C": [0.002] * 40, "D": [0.001] * 40}, index=idx(40)
        )
        w = funding_carry_weights(f, lookback=5, quantile=0.25, gross=1.0)
        last = w.iloc[-1]
        self.assertAlmostEqual(last.sum(), 0.0)
        self.assertAlmostEqual(last.abs().sum(), 1.0)
        self.assertAlmostEqual(last["D"], 0.5)  # lowest funding: long
        self.assertAlmostEqual(last["A"], -0.5)  # highest funding: short (collects it)
        self.assertEqual(w.iloc[:4].abs().sum().sum(), 0.0)  # warm-up is flat

    def test_tsmom_follows_trend(self):
        n = 200
        c = pd.DataFrame(
            {"UP": 100 * 1.003 ** np.arange(n), "DOWN": 100 * 0.997 ** np.arange(n)}, index=idx(n)
        )
        w = tsmom_weights(c, lookback=30, vol_lookback=20)
        self.assertGreater(w["UP"].iloc[-1], 0)
        self.assertLess(w["DOWN"].iloc[-1], 0)

class NewSignalTests(unittest.TestCase):
    def setUp(self):
        n = 60
        self.close = pd.DataFrame(
            {"W": 100 * 1.01 ** np.arange(n), "M": 100.0 + 0 * np.arange(n), "L": 100 * 0.99 ** np.arange(n)},
            index=idx(n),
        )

    def test_momentum_long_winner_short_loser(self):
        from ariyan_crypto.signals import xs_momentum_weights
        w = xs_momentum_weights(self.close, lookback=10, quantile=0.34).iloc[-1]
        self.assertGreater(w["W"], 0)
        self.assertLess(w["L"], 0)
        self.assertAlmostEqual(w.sum(), 0.0)

    def test_reversal_is_the_opposite(self):
        from ariyan_crypto.signals import reversal_weights
        w = reversal_weights(self.close, lookback=5, quantile=0.34).iloc[-1]
        self.assertLess(w["W"], 0)
        self.assertGreater(w["L"], 0)

    def test_top_n_by_volume_and_eligibility(self):
        from ariyan_crypto.signals import reversal_weights, top_n_by_volume
        vol = pd.DataFrame({"W": 1.0, "M": 5.0, "L": 9.0}, index=self.close.index)
        mask = top_n_by_volume(vol, n=2, lookback=5)
        self.assertEqual(mask.iloc[-1].to_dict(), {"W": False, "M": True, "L": True})
        self.assertFalse(mask.iloc[:4].any().any())  # warm-up
        w = reversal_weights(self.close, lookback=5, quantile=0.5, eligible=mask).iloc[-1]
        self.assertEqual(w["W"], 0.0)  # excluded asset never gets a weight

    def test_funding_carry_respects_eligible(self):
        f = pd.DataFrame({"A": [0.004] * 30, "B": [0.003] * 30, "C": [0.001] * 30}, index=idx(30))
        el = pd.DataFrame({"A": False, "B": True, "C": True}, index=f.index)
        w = funding_carry_weights(f, lookback=5, quantile=0.5, eligible=el).iloc[-1]
        self.assertEqual(w["A"], 0.0)
        self.assertLess(w["B"], 0)
        self.assertGreater(w["C"], 0)


class RegistryTests(unittest.TestCase):
    def test_chain_counts_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as d:
            reg = Registry(Path(d) / "trials.jsonl")
            reg.log_trial("carry", "lb30", {"lookback": 30}, {"sharpe": 0.4})
            reg.log_trial("carry", "lb60", {"lookback": 60}, {"sharpe": 0.1})
            reg.log_trial("trend", "lb90", {"lookback": 90}, {"sharpe": -0.2})
            self.assertEqual(reg.n_trials(), 3)
            self.assertEqual(reg.n_trials("carry"), 2)
            self.assertTrue(reg.verify())
            lines = reg.path.read_text().splitlines()
            rec = json.loads(lines[1])
            rec["metrics"]["sharpe"] = 3.0
            lines[1] = json.dumps(rec, sort_keys=True)
            reg.path.write_text("\n".join(lines) + "\n")
            self.assertFalse(reg.verify())


if __name__ == "__main__":
    unittest.main()
