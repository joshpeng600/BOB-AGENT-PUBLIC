from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.helpers import make_dataset, write_csv
from tools.common import ValidationError
from tools.run_experiment import ensure_aligned_lengths
from tools.validate_predictions import HEADER, validate


class PredictionTests(unittest.TestCase):
    def test_valid_prediction_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            data_dir = make_dataset(base / "data")
            prediction = base / "predictions.csv"
            write_csv(
                prediction,
                HEADER,
                [[0, "u1", "v1", 0.9], [1, "u1", "v2", 0.1]],
            )
            self.assertEqual(validate(prediction, data_dir, "valid")["rows"], 2)

    def test_array_length_mismatch_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValidationError, "array length mismatch"):
            ensure_aligned_lengths([1, 2], [1])

    def test_prediction_row_count_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            data_dir = make_dataset(base / "data")
            prediction = base / "predictions.csv"
            write_csv(prediction, HEADER, [[0, "u1", "v1", 0.9]])
            with self.assertRaisesRegex(ValidationError, "expected 2"):
                validate(prediction, data_dir, "valid")

    def test_nan_and_inf_are_rejected(self) -> None:
        for invalid in ("NaN", "Inf", "-Inf"):
            with self.subTest(invalid=invalid), tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                data_dir = make_dataset(base / "data")
                prediction = base / "predictions.csv"
                write_csv(
                    prediction,
                    HEADER,
                    [[0, "u1", "v1", invalid], [1, "u1", "v2", 0.1]],
                )
                with self.assertRaisesRegex(ValidationError, "NaN/Inf"):
                    validate(prediction, data_dir, "valid")


if __name__ == "__main__":
    unittest.main()
