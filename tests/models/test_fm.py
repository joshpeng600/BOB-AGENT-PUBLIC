import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np

from src.models.fm import FactorizationMachine


def load_official_baseline():
    baseline_dir = Path(__file__).resolve().parents[2] / "baseline"
    sys.path.insert(0, str(baseline_dir))
    try:
        spec = importlib.util.spec_from_file_location("official_baseline_for_d_test", baseline_dir / "baseline.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


class FactorizationMachineTests(unittest.TestCase):
    def setUp(self):
        self.features = np.asarray(
            [[0, 3, 6], [1, 4, 7], [2, 5, 8], [0, 4, 8]], dtype=np.int32
        )
        self.labels = np.asarray([1, 0, 1, 0], dtype=np.float32)

    def test_pointwise_behaviour_matches_official_fm(self):
        official_module = load_official_baseline()
        official = official_module.FM(dim=9, k=4, lr=0.003, l2=1e-6, seed=17)
        working = FactorizationMachine(
            feature_dim=9,
            embedding_dim=4,
            learning_rate=0.003,
            l2=1e-6,
            seed=17,
        )
        np.testing.assert_allclose(working.predict_scores(self.features), official.predict(self.features))
        self.assertAlmostEqual(working.step(self.features, self.labels), official.step(self.features, self.labels))
        np.testing.assert_allclose(working.V, official.V, rtol=1e-6, atol=1e-7)
        np.testing.assert_allclose(working.W, official.W, rtol=1e-6, atol=1e-7)
        self.assertAlmostEqual(float(working.b), float(official.b), places=7)

    def test_predict_scores_preserves_count_order_and_batch_independence(self):
        model = FactorizationMachine(9, embedding_dim=4, seed=2)
        all_at_once = model.predict_scores(self.features)
        batched = model.predict_scores(self.features, batch_size=1)
        self.assertEqual(all_at_once.shape, (len(self.features),))
        np.testing.assert_array_equal(all_at_once, batched)
        reversed_scores = model.predict_scores(self.features[::-1])
        np.testing.assert_array_equal(reversed_scores, all_at_once[::-1])

    def test_fixed_seed_is_reproducible(self):
        first = FactorizationMachine(9, embedding_dim=4, seed=9)
        second = FactorizationMachine(9, embedding_dim=4, seed=9)
        self.assertEqual(first.step(self.features, self.labels), second.step(self.features, self.labels))
        np.testing.assert_array_equal(first.predict_scores(self.features), second.predict_scores(self.features))


if __name__ == "__main__":
    unittest.main()
