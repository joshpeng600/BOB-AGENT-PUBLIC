import unittest

import numpy as np

from src.models.fm import FactorizationMachine
from src.training.config import ResolvedTrainingConfig
from src.training.trainer import fit_pointwise


class ConfigAndTrainerTests(unittest.TestCase):
    def test_config_resolves_documented_aliases_and_rejects_unknown_fields(self):
        config = ResolvedTrainingConfig.from_mapping(
            {"seed": 3, "batch": 4, "epoch": 2, "patience": 1, "max_batches": 1}
        )
        self.assertEqual(config.batch_size, 4)
        self.assertEqual(config.epochs, 2)
        with self.assertRaisesRegex(ValueError, "unknown training config"):
            ResolvedTrainingConfig.from_mapping({"test_split": True})

    def test_trainer_is_reproducible_and_honours_max_batches(self):
        features = np.asarray(
            [[0, 3], [1, 4], [2, 5], [0, 4], [1, 5], [2, 3]], dtype=np.int32
        )
        labels = np.asarray([1, 0, 1, 0, 1, 0], dtype=np.float32)
        config = ResolvedTrainingConfig(seed=8, batch_size=2, epochs=3, patience=3, max_batches=1)

        def run():
            model = FactorizationMachine(6, embedding_dim=3, seed=8)
            result = fit_pointwise(
                model,
                features,
                labels,
                features,
                lambda scores: float(scores.mean()),
                config,
            )
            return result, model.predict_scores(features)

        first_result, first_scores = run()
        second_result, second_scores = run()
        self.assertEqual(first_result, second_result)
        np.testing.assert_array_equal(first_scores, second_scores)
        self.assertLessEqual(first_result.epochs_ran, config.epochs)


if __name__ == "__main__":
    unittest.main()
