import contextlib
import csv
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import safe_evaluate


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
        self.assertEqual(evidence["evaluator_role"], "E")
        self.assertEqual(evidence["split"], "valid")
        self.assertTrue(evidence["worktree_clean"])
        self.assertFalse(evidence["test_access"])
        self.assertEqual(
            evidence["primary"],
            (evidence["GAUC"] + evidence["nDCG@5"]) / 2.0,
        )

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

    def test_dirty_worktree_is_denied_before_evaluation(self):
        argv = [
            "safe_evaluate",
            "--prediction",
            str(self.prediction),
            "--split",
            "valid",
            "--data-dir",
            str(self.data_dir),
            "--output",
            str(self.output),
        ]
        stdout = io.StringIO()
        with (
            patch.object(sys, "argv", argv),
            patch.object(safe_evaluate, "git_is_dirty", return_value=True),
            contextlib.redirect_stdout(stdout),
        ):
            result = safe_evaluate.main()
        self.assertNotEqual(result, 0)
        self.assertIn("Worktree is dirty", stdout.getvalue())
        self.assertFalse(self.output.exists())

    def test_output_cannot_overwrite_immutable_prediction(self):
        self.prediction.write_text("immutable prediction bytes\n", encoding="utf-8")
        before = self.prediction.read_bytes()
        argv = [
            "safe_evaluate",
            "--prediction",
            str(self.prediction),
            "--split",
            "valid",
            "--data-dir",
            str(self.data_dir),
            "--output",
            str(self.prediction),
        ]
        stdout = io.StringIO()
        with patch.object(sys, "argv", argv), contextlib.redirect_stdout(stdout):
            result = safe_evaluate.main()
        self.assertNotEqual(result, 0)
        self.assertIn("must not overwrite", stdout.getvalue())
        self.assertEqual(self.prediction.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
