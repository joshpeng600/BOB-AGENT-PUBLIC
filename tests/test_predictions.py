from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.helpers import LOG_HEADER, make_dataset, write_csv
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

    def test_header_and_canonical_row_ids_are_strict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            data_dir = make_dataset(base / "data")
            prediction = base / "predictions.csv"
            write_csv(
                prediction,
                ["user_id", "video_id", "score"],
                [["u1", "v1", 0.9]],
            )
            with self.assertRaisesRegex(ValidationError, "header must be"):
                validate(prediction, data_dir, "valid")
            for noncanonical in ("00", "+0"):
                with self.subTest(row_id=noncanonical):
                    write_csv(
                        prediction,
                        HEADER,
                        [[noncanonical, "u1", "v1", 0.9], [1, "u1", "v2", 0.1]],
                    )
                    with self.assertRaisesRegex(ValidationError, "expected contiguous"):
                        validate(prediction, data_dir, "valid")

    def test_duplicate_user_video_rows_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            data_dir = make_dataset(base / "data")
            write_csv(
                data_dir / "log_standard_4_22_to_5_08_pure.csv",
                LOG_HEADER,
                [
                    [20220422, "u1", "v1", 1, 1000, 1],
                    [20220423, "u1", "v1", 1, 1000, 0],
                ],
            )
            prediction = base / "predictions.csv"
            write_csv(
                prediction,
                HEADER,
                [[0, "u1", "v1", 0.9], [1, "u1", "v1", 0.1]],
            )
            self.assertEqual(validate(prediction, data_dir, "valid")["rows"], 2)

    def test_non_valid_split_is_denied_before_data_access(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ValidationError, "only permits split=valid"):
                validate(root / "missing.csv", root / "missing-data", "test")

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
