from __future__ import annotations

import json
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import numpy as np

from tests.helpers import make_dataset
from tools.common import write_json
from tools.run_experiment import main
from tools.validate_contract import validate_contract
from tools.validate_predictions import validate


def fake_starter_modules() -> dict[str, types.ModuleType]:
    package = types.ModuleType("starter")
    package.__path__ = []  # type: ignore[attr-defined]
    data_module = types.ModuleType("starter.data")
    evaluate_module = types.ModuleType("starter.evaluate")
    baseline_module = types.ModuleType("starter.baseline")

    train = [
        (20220408, "u1", "v1", "a1", "1", 1000.0, 0),
        (20220409, "u2", "v2", "a2", "1", 2000.0, 1),
    ]
    valid = [
        (20220422, "u1", "v1", "a1", "1", 1000.0, 1),
        (20220423, "u1", "v2", "a2", "1", 2000.0, 0),
    ]

    def load(_data_dir: str):
        return {"train": train, "valid": valid, "test": []}

    def encode(_splits):
        encoded = {
            "train": (np.asarray([[0], [1]], dtype=np.int32), np.asarray([0, 1], dtype=np.float32), ["u1", "u2"]),
            "valid": (np.asarray([[0], [1]], dtype=np.int32), np.asarray([1, 0], dtype=np.float32), ["u1", "u1"]),
            "test": (np.empty((0, 1), dtype=np.int32), np.asarray([], dtype=np.float32), []),
        }
        return encoded, 2

    def evaluate(users, labels, scores):
        if not (len(users) == len(labels) == len(scores)):
            raise AssertionError("fixture alignment failure")
        return {"GAUC": 1.0, "nDCG@5": 1.0, "primary": 1.0, "users": 1, "rows": 2}

    class FM:
        def __init__(self, field_dim, k, lr, l2, seed):
            self.V = np.zeros((field_dim, k), dtype=float)
            self.W = np.zeros(field_dim, dtype=float)
            self.b = 0.0

        def step(self, features, labels):
            self.b += float(np.mean(labels)) * 0.01

        def predict(self, features):
            return np.asarray([1.0 - float(row[0]) for row in features]) + self.b

    data_module.load = load  # type: ignore[attr-defined]
    data_module.encode = encode  # type: ignore[attr-defined]
    evaluate_module.evaluate = evaluate  # type: ignore[attr-defined]
    baseline_module.FM = FM  # type: ignore[attr-defined]
    package.data = data_module  # type: ignore[attr-defined]
    package.evaluate = evaluate_module  # type: ignore[attr-defined]
    package.baseline = baseline_module  # type: ignore[attr-defined]
    return {
        "starter": package,
        "starter.data": data_module,
        "starter.evaluate": evaluate_module,
        "starter.baseline": baseline_module,
    }


class RunExperimentTests(unittest.TestCase):
    def test_synthetic_valid_only_smoke_writes_complete_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            data_dir = make_dataset(base / "data")
            output_dir = base / "run"
            config_path = base / "exp_smoke.json"
            write_json(
                config_path,
                {
                    "exp_id": "exp_smoke",
                    "model": "FM",
                    "batch": 2,
                    "max_epochs": 2,
                    "patience": 1,
                    "evaluation_split": "valid",
                },
            )
            argv = [
                "run_experiment.py",
                "--config", str(config_path),
                "--data-dir", str(data_dir),
                "--output-dir", str(output_dir),
                "--seed", "7",
                "--max-batches", "1",
                "--mode", "valid-only",
            ]
            with patch.dict(sys.modules, fake_starter_modules()), patch.object(sys, "argv", argv):
                with redirect_stdout(StringIO()):
                    self.assertEqual(main(), 0)
            manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["exit_code"], 0)
            self.assertEqual(manifest["exp_id"], "exp_smoke")
            self.assertNotEqual(manifest["prediction_hash"], "not-produced")
            self.assertNotEqual(manifest["checkpoint_hash"], "not-produced")
            validate_contract("run-manifest", manifest)
            self.assertEqual(validate(output_dir / "valid_predictions.csv", data_dir, "valid")["rows"], 2)


if __name__ == "__main__":
    unittest.main()
