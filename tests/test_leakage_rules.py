import unittest

from src.data.feature_registry import FeatureSpec, validate_registry


class LeakageRuleTests(unittest.TestCase):
    def test_all_baseline_features_fit_on_train_only(self):
        validate_registry()

    def test_registry_rejects_validation_fitted_statistics(self):
        unsafe = FeatureSpec("bad_popularity", ("video_id",), "valid", "impression", "float32", 1, "zero")
        with self.assertRaises(ValueError):
            validate_registry((unsafe,))

    def test_registry_rejects_current_or_future_history(self):
        unsafe = FeatureSpec("bad_history", ("user_id",), "train", "after_impression", "float32", 1, "zero")
        with self.assertRaises(ValueError):
            unsafe.validate()


if __name__ == "__main__":
    unittest.main()
