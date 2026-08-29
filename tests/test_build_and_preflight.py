from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.helpers import make_dataset
from tools.build_dev_dataset import build
from tools.common import VALID_END, ValidationError
from tools.preflight import inspect_data


class BuildAndPreflightTests(unittest.TestCase):
    def test_build_filters_held_out_rows_and_writes_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = make_dataset(base / "raw", include_test=True)
            output = base / "dev"
            manifest = build(source, output, VALID_END)
            self.assertEqual(manifest["test_rows"], 0)
            self.assertEqual(manifest["max_date"], VALID_END - 5)
            self.assertTrue((output / "video_features_basic_pure.csv").is_file())
            stored = json.loads((output / "dataset_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(stored["rows"], 4)
            result = inspect_data(output, "experiment")
            self.assertEqual(result["test_rows"], 0)
            self.assertEqual(result["label_values"], [0, 1])

    def test_build_rejects_cutoff_after_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = make_dataset(base / "raw", include_test=True)
            with self.assertRaisesRegex(ValidationError, "crosses the experiment cutoff"):
                build(source, base / "dev", 20220429)

    def test_preflight_rejects_test_date(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = make_dataset(Path(tmp), include_test=True)
            with self.assertRaisesRegex(ValidationError, "after cutoff"):
                inspect_data(data_dir, "experiment")

    def test_preflight_rejects_test_scoring_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = make_dataset(Path(tmp), include_test=False)
            for config in ({"score_test": True}, {"evaluation": {"split": "test"}}):
                with self.subTest(config=config):
                    with self.assertRaisesRegex(ValidationError, "test .*request denied"):
                        inspect_data(data_dir, "experiment", config)


if __name__ == "__main__":
    unittest.main()
