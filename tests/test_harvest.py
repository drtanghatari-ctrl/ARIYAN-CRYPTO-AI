import unittest

import numpy as np
import pandas as pd

from ariyan_crypto.harvest import COST_PER_UNIT_NOTIONAL, harvest_weights, hedged_returns, run_harvest


def idx(n):
    return pd.date_range("2024-01-01", periods=n, freq="D")


class HarvestTests(unittest.TestCase):
    def test_price_risk_cancels_and_funding_is_received(self):
        px = pd.DataFrame({"A": 100 * 1.05 ** np.arange(6)}, index=idx(6))  # spot and perp move together
        f = pd.DataFrame({"A": [0.001] * 6}, index=idx(6))
        r = hedged_returns(px, px, f)
        self.assertAlmostEqual(r["A"].iloc[3], 0.001)  # only funding remains
        basis = hedged_returns(px, px * 1.0, f * 0)
        self.assertAlmostEqual(basis["A"].iloc[3], 0.0)

    def test_basis_widening_hurts(self):
        spot = pd.DataFrame({"A": [100.0, 99.0]}, index=idx(2))
        perp = pd.DataFrame({"A": [100.0, 100.0]}, index=idx(2))
        r = hedged_returns(spot, perp, pd.DataFrame({"A": [0.0, 0.0]}, index=idx(2)))
        self.assertAlmostEqual(r["A"].iloc[1], -0.01)

    def test_weights_use_hysteresis_and_cap(self):
        n = 40
        cols = list("ABCDEF")
        f = pd.DataFrame(0.0, index=idx(n), columns=cols)
        f.loc[:, ["A", "B", "C", "D", "E"]] = 0.0004
        f.loc[idx(n)[33:], "A"] = 0.00005  # A decays after entry: positive but below hurdle -> stays held
        f.loc[idx(n)[35:], "B"] = -0.001  # B turns negative -> exits eventually
        px = pd.DataFrame(100.0, index=idx(n), columns=cols)
        vol = pd.DataFrame(1e8, index=idx(n), columns=cols)
        w = harvest_weights(px, px, f, vol, top_n=6, enter_hurdle=0.0002, lookback=5)
        last = w.iloc[-1]
        self.assertGreater(last["A"], 0)  # hysteresis kept A
        self.assertEqual(last["F"], 0.0)  # never entered
        self.assertEqual(last["B"], 0.0)  # funding turned negative -> exited
        self.assertGreater(last["C"], 0)
        self.assertLessEqual(w.sum(axis=1).max(), 0.5 + 1e-12)
        self.assertEqual(w.iloc[:4].abs().sum().sum(), 0.0)  # warm-up

    def test_costs_charged_on_entry_and_scaled(self):
        n = 6
        w = pd.DataFrame({"A": [0.0, 0.5, 0.5, 0.5, 0.5, 0.5]}, index=idx(n))
        r = pd.DataFrame({"A": [0.0] * n}, index=idx(n))
        out = run_harvest(w, r)
        self.assertAlmostEqual(out["net"].sum(), -0.5 * COST_PER_UNIT_NOTIONAL)
        out2 = run_harvest(w, r, cost_multiplier=2.0)
        self.assertAlmostEqual(out2["net"].sum(), -2 * 0.5 * COST_PER_UNIT_NOTIONAL)

    def test_no_lookahead(self):
        w = pd.DataFrame({"A": [0.0, 0.5, 0.5]}, index=idx(3))
        r = pd.DataFrame({"A": [0.0, 0.10, 0.0]}, index=idx(3))
        out = run_harvest(w, r)
        self.assertAlmostEqual(out["gross"].iloc[1], 0.0)  # weight decided on day 1 cannot earn day 1


if __name__ == "__main__":
    unittest.main()
