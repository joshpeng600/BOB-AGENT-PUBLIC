import csv
import math
import tempfile
import unittest
from pathlib import Path

from tools.prediction_contract import (
    PredictionContractError,
    validate_evaluator_arrays,
    validate_prediction_file,
)


def official_row(user_id, video_id, label=0):
    return (20220422, user_id, video_id, "author", "tab", 1000.0, label)


class PredictionContractTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tempdir.name) / "prediction.csv"
        self.rows = [official_row("u1", "v1"), official_row("u2", "v2", 1)]

    def tearDown(self):
        self.tempdir.cleanup()

    def write(self, header, records):
        with self.path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            writer.writerows(records)

    def test_accepts_exact_contract(self):
        self.write(
            ["row_id", "user_id", "video_id", "score"],
            [[0, "u1", "v1", 0.1], [1, "u2", "v2", -2.0]],
        )
        self.assertEqual(validate_prediction_file(self.path, self.rows), [0.1, -2.0])

    def test_duplicate_user_video_is_allowed_when_row_id_differs(self):
        duplicate_rows = [official_row("u1", "v1"), official_row("u1", "v1")]
        self.write(
            ["row_id", "user_id", "video_id", "score"],
            [[0, "u1", "v1", 0.1], [1, "u1", "v1", 0.2]],
        )
        self.assertEqual(len(validate_prediction_file(self.path, duplicate_rows)), 2)

    def test_rejects_wrong_header(self):
        self.write(["user_id", "video_id", "score"], [])
        with self.assertRaises(PredictionContractError):
            validate_prediction_file(self.path, self.rows)

    def test_rejects_short_file(self):
        self.write(
            ["row_id", "user_id", "video_id", "score"],
            [[0, "u1", "v1", 0.1]],
        )
        with self.assertRaises(PredictionContractError):
            validate_prediction_file(self.path, self.rows)

    def test_rejects_long_file(self):
        self.write(
            ["row_id", "user_id", "video_id", "score"],
            [[0, "u1", "v1", 0.1], [1, "u2", "v2", 0.2], [2, "u3", "v3", 0.3]],
        )
        with self.assertRaises(PredictionContractError):
            validate_prediction_file(self.path, self.rows)

    def test_rejects_noncontinuous_row_id(self):
        self.write(
            ["row_id", "user_id", "video_id", "score"],
            [[0, "u1", "v1", 0.1], [7, "u2", "v2", 0.2]],
        )
        with self.assertRaises(PredictionContractError):
            validate_prediction_file(self.path, self.rows)

    def test_rejects_user_or_video_misalignment(self):
        self.write(
            ["row_id", "user_id", "video_id", "score"],
            [[0, "wrong", "v1", 0.1], [1, "u2", "v2", 0.2]],
        )
        with self.assertRaises(PredictionContractError):
            validate_prediction_file(self.path, self.rows)

    def test_rejects_nan_and_inf(self):
        for invalid in ("NaN", "Inf", "-Inf"):
            with self.subTest(invalid=invalid):
                self.write(
                    ["row_id", "user_id", "video_id", "score"],
                    [[0, "u1", "v1", invalid], [1, "u2", "v2", 0.2]],
                )
                with self.assertRaises(PredictionContractError):
                    validate_prediction_file(self.path, self.rows)

    def test_evaluator_arrays_must_be_equal_binary_finite_and_nonempty(self):
        with self.assertRaises(PredictionContractError):
            validate_evaluator_arrays(["u1"], [0, 1], [0.2])
        with self.assertRaises(PredictionContractError):
            validate_evaluator_arrays(["u1"], [2], [0.2])
        with self.assertRaises(PredictionContractError):
            validate_evaluator_arrays([""], [0], [0.2])
        with self.assertRaises(PredictionContractError):
            validate_evaluator_arrays(["u1"], [0], [math.nan])


if __name__ == "__main__":
    unittest.main()
