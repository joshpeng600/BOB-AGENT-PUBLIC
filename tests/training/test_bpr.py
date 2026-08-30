import unittest

import numpy as np

from src.models.fm import FactorizationMachine
from src.training.bpr import fit_bpr_epoch, sample_same_user_pairs
from src.training.config import ResolvedTrainingConfig


class BprTests(unittest.TestCase):
    def test_pairs_are_same_user_and_skip_ineligible_users(self):
        users = np.asarray(["mixed", "mixed", "positive", "positive", "negative"])
        labels = np.asarray([1, 0, 1, 1, 0], dtype=np.float32)
        positive, negative, coverage = sample_same_user_pairs(users, labels, seed=5)
        self.assertTrue(np.all(users[positive] == users[negative]))
        self.assertTrue(np.all(labels[positive] == 1))
        self.assertTrue(np.all(labels[negative] == 0))
        self.assertEqual(coverage.total_users, 3)
        self.assertEqual(coverage.eligible_users, 1)
        self.assertEqual(coverage.pair_count, 1)
        self.assertEqual(coverage.pairs, 1)

    def test_no_valid_pair_has_readable_failure(self):
        with self.assertRaisesRegex(ValueError, "no valid BPR pairs"):
            sample_same_user_pairs(["positive", "positive", "negative"], np.asarray([1, 1, 0]))

    def test_fixed_seed_reproduces_sampling(self):
        users = ["u", "u", "u", "u"]
        labels = np.asarray([1, 1, 0, 0])
        first = sample_same_user_pairs(users, labels, negatives_per_positive=3, seed=12)
        second = sample_same_user_pairs(users, labels, negatives_per_positive=3, seed=12)
        np.testing.assert_array_equal(first[0], second[0])
        np.testing.assert_array_equal(first[1], second[1])
        self.assertEqual(first[2], second[2])

    def test_bpr_training_increases_positive_negative_score_gap(self):
        features = np.asarray([[0, 2], [1, 3]], dtype=np.int32)
        labels = np.asarray([1, 0], dtype=np.float32)
        users = ["same", "same"]
        model = FactorizationMachine(4, embedding_dim=3, learning_rate=0.03, l2=0.0, seed=1)
        before = float(np.diff(model.predict_scores(features)[::-1])[0])
        config = ResolvedTrainingConfig(seed=1, batch_size=1, epochs=1, patience=1)
        for epoch in range(8):
            fit_bpr_epoch(model, features, labels, users, config, epoch=epoch)
        after = float(model.predict_scores(features)[0] - model.predict_scores(features)[1])
        self.assertGreater(after, before)


if __name__ == "__main__":
    unittest.main()
