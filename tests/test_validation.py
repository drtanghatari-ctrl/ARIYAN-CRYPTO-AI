import unittest

import numpy as np

from ariyan_crypto.validation import (
    deflated_sharpe,
    expected_max_sharpe,
    psr,
    purged_kfold,
    sharpe,
    walk_forward_splits,
)


class ValidationTests(unittest.TestCase):
    def test_expected_max_sharpe_grows_with_trials(self):
        a = expected_max_sharpe(2, 0.001)
        b = expected_max_sharpe(100, 0.001)
        c = expected_max_sharpe(10000, 0.001)
        self.assertLess(a, b)
        self.assertLess(b, c)
        self.assertEqual(expected_max_sharpe(1, 0.001), 0.0)

    def test_real_edge_survives_deflation(self):
        r = np.random.default_rng(0).normal(0.002, 0.01, 1000)
        self.assertGreater(deflated_sharpe(r, n_trials=20), 0.99)

    def test_noise_does_not_survive_many_trials(self):
        r = np.random.default_rng(1).normal(0.0, 0.01, 1000)
        self.assertLess(deflated_sharpe(r, n_trials=200), 0.5)
        self.assertLess(deflated_sharpe(r, n_trials=200), psr(r, 0.0) + 1e-12)

    def test_more_trials_lower_dsr(self):
        r = np.random.default_rng(2).normal(0.0006, 0.01, 800)
        self.assertGreater(deflated_sharpe(r, 5), deflated_sharpe(r, 500))

    def test_sharpe_zero_vol(self):
        self.assertEqual(sharpe([0.0] * 10), 0.0)

    def test_purged_kfold_has_no_leakage(self):
        n, h, e = 100, 5, 3
        for tr, te in purged_kfold(n, k=5, horizon=h, embargo=e):
            a, b = te.min(), te.max() + 1
            self.assertFalse(np.any((tr >= a - h) & (tr < b + e)))
            self.assertEqual(len(set(tr) & set(te)), 0)

    def test_walk_forward_test_after_train(self):
        splits = list(walk_forward_splits(200, train_size=100, test_size=20))
        self.assertGreater(len(splits), 1)
        for tr, te in splits:
            self.assertLess(tr.max(), te.min())
        self.assertEqual(splits[1][1][0] - splits[0][1][0], 20)


if __name__ == "__main__":
    unittest.main()
