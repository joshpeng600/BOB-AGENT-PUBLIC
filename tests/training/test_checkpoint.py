import tempfile
import unittest
from pathlib import Path

import numpy as np

from src.models.fm import FactorizationMachine
from src.training.checkpoint import load_checkpoint, save_checkpoint


class CheckpointTests(unittest.TestCase):
    def test_checkpoint_restores_parameters_optimizer_and_predictions(self):
        features = np.asarray([[0, 2], [1, 3], [0, 3]], dtype=np.int32)
        labels = np.asarray([1, 0, 1], dtype=np.float32)
        model = FactorizationMachine(4, embedding_dim=3, seed=4)
        model.step(features, labels)
        expected = model.predict_scores(features)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.npz"
            save_checkpoint(
                path,
                model,
                config={"seed": 4, "batch_size": 3},
                epoch=1,
                best_metric=0.5,
            )
            restored, metadata = load_checkpoint(path)
        np.testing.assert_array_equal(restored.predict_scores(features), expected)
        self.assertEqual(restored.t, model.t)
        for field in ("V", "W", "mV", "vV", "mW", "vW"):
            np.testing.assert_array_equal(getattr(restored, field), getattr(model, field))
        self.assertEqual(float(restored.b), float(model.b))
        self.assertEqual(metadata["epoch"], 1)
        self.assertEqual(metadata["best_metric"], 0.5)
        self.assertEqual(metadata["config"]["seed"], 4)


if __name__ == "__main__":
    unittest.main()
