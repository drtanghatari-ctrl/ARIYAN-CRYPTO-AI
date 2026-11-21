import unittest

import numpy as np
import pandas as pd

from ariyan_crypto.backtest import CostModel, metrics, run_backtest

NO_COST = CostModel(0.0, 0.0)


def idx(n):
    return pd.date_range("2024-01-01", periods=n, freq="D")


class BacktestTests(unittest.TestCase):
    def test_signal_cannot_earn_its_own_bar(self):
        close = pd.DataFrame({"A": [100.0] * 5 + [110.0] * 5}, index=idx(10))
        w = pd.DataFrame({"A": [0.0] * 5 + [1.0] * 5}, index=idx(10))  # decided on the jump bar
        res = run_backtest(close, w, cost=NO_COST, max_drawdown=1.0)
        self.assertAlmostEqual(res.returns.sum(), 0.0)

    def test_past_unchanged_by_future_data(self):
        rng = np.random.default_rng(0)
        c = pd.DataFrame({"A": 100 * np.cumprod(1 + rng.normal(0, 0.01, 60))}, index=idx(60))
        w = pd.DataFrame({"A": np.sign(rng.normal(size=60))}, index=idx(60))
        a = run_backtest(c, w, cost=NO_COST, max_drawdown=1.0).returns
        c2 = c.copy()
        c2.iloc[-1] *= 1.5
        b = run_backtest(c2, w, cost=NO_COST, max_drawdown=1.0).returns
        np.testing.assert_allclose(a.iloc[:-1], b.iloc[:-1])

    def test_costs_reduce_returns_by_turnover(self):
        rng = np.random.default_rng(1)
        c = pd.DataFrame({"A": 100 * np.cumprod(1 + rng.normal(0, 0.01, 80))}, index=idx(80))
        w = pd.DataFrame({"A": [1.0, -1.0] * 40}, index=idx(80))
        free = run_backtest(c, w, cost=NO_COST, max_drawdown=1.0)
        paid = run_backtest(c, w, cost=CostModel(0.0005, 0.0005), max_drawdown=1.0)
        expected = free.returns.sum() - paid.turnover.sum() * 0.001
        self.assertAlmostEqual(paid.returns.sum(), expected)
        self.assertLess(paid.returns.sum(), free.returns.sum())

    def test_long_pays_positive_funding(self):
        c = pd.DataFrame({"A": [100.0] * 11}, index=idx(11))
        w = pd.DataFrame({"A": [1.0] * 11}, index=idx(11))
        f = pd.DataFrame({"A": [0.001] * 11}, index=idx(11))
        res = run_backtest(c, w, funding=f, cost=NO_COST, max_drawdown=1.0)
        self.assertAlmostEqual(res.returns.sum(), -0.01)  # 10 held bars
        res_short = run_backtest(c, -w, funding=f, cost=NO_COST, max_drawdown=1.0)
        self.assertAlmostEqual(res_short.returns.sum(), 0.01)

    def test_kill_switch_flattens_after_drawdown(self):
        c = pd.DataFrame({"A": 100 * 0.95 ** np.arange(20)}, index=idx(20))
        w = pd.DataFrame({"A": [1.0] * 20}, index=idx(20))
        res = run_backtest(c, w, cost=NO_COST, max_drawdown=0.10, cooldown=5)
        self.assertGreaterEqual(res.halts, 1)
        self.assertTrue((res.returns.iloc[4:9] == 0.0).all())

    def test_gross_cap_applied(self):
        c = pd.DataFrame({"A": [100.0, 101.0, 102.0, 103.0]}, index=idx(4))
        w = pd.DataFrame({"A": [10.0] * 4}, index=idx(4))
        res = run_backtest(c, w, cost=NO_COST, max_gross=2.0, max_drawdown=1.0)
        self.assertAlmostEqual(res.returns.iloc[1], 2.0 * 0.01)

    def test_metrics_keys(self):
        c = pd.DataFrame({"A": np.linspace(100, 120, 50)}, index=idx(50))
        w = pd.DataFrame({"A": [1.0] * 50}, index=idx(50))
        m = metrics(run_backtest(c, w, cost=NO_COST, max_drawdown=1.0))
        self.assertGreater(m["total_return"], 0)
        self.assertLessEqual(m["max_drawdown"], 0.0)


if __name__ == "__main__":
    unittest.main()
