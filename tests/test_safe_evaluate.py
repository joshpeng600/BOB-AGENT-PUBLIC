import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class SafeEvaluateIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.data_dir = self.root / "data"
        self.data_dir.mkdir()
        self.prediction = self.root / "prediction.csv"
        self.output = self.root / "metrics.json"

    def tearDown(self):
        self.tempdir.cleanup()

    def write_log(self, filename, records):
        with (self.data_dir / filename).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["date", "user_id", "video_id", "long_view"],
            )
            writer.writeheader()
            writer.writerows(records)

    def test_valid_split_calls_official_evaluator_and_writes_evidence(self):
        self.write_log(
            "log_standard_4_08_to_4_21_pure.csv",
            [{"date": 20220421, "user_id": "train", "video_id": "v0", "long_view": "0"}],
        )
        self.write_log(
            "log_standard_4_22_to_5_08_pure.csv",
            [
                {"date": 20220422, "user_id": "u1", "video_id": "v1", "long_view": "1"},
                {"date": 20220422, "user_id": "u1", "video_id": "v2", "long_view": "0"},
                {"date": 20220423, "user_id": "u2", "video_id": "v3", "long_view": "0"},
                {"date": 20220423, "user_id": "u2", "video_id": "v4", "long_view": "1"},
            ],
        )
        with self.prediction.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["row_id", "user_id", "video_id", "score"])
            writer.writerows(
                [[0, "u1", "v1", 0.9], [1, "u1", "v2", 0.1],
                 [2, "u2", "v3", 0.2], [3, "u2", "v4", 0.8]]
            )
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.safe_evaluate",
                "--prediction",
                str(self.prediction),
                "--split",
                "valid",
                "--data-dir",
                str(self.data_dir),
                "--output",
                str(self.output),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        evidence = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(evidence["rows"], 4)
        self.assertEqual(evidence["users"], 2)
        self.assertEqual(evidence["primary"], 1.0)
        self.assertEqual(len(evidence["evaluator_hash"]), 64)

    def test_test_split_is_denied_without_approval_before_data_access(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.safe_evaluate",
                "--prediction",
                str(self.prediction),
                "--split",
                "test",
                "--data-dir",
                str(self.data_dir),
                "--output",
                str(self.output),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Normal mode only permits valid", result.stdout)


if __name__ == "__main__":
    unittest.main()
