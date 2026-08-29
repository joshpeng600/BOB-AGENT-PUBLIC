from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.common import ValidationError, sha256_file, write_json
from tools.validate_contract import validate_contract
from tools.verify_protected_files import verify


class ProtectedAndContractTests(unittest.TestCase):
    def test_protected_hash_change_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protected = root / "starter" / "evaluate.py"
            protected.parent.mkdir(parents=True)
            protected.write_text("official\n", encoding="utf-8")
            manifest = root / "governance" / "protected_files.json"
            write_json(manifest, {"files": {"starter/evaluate.py": sha256_file(protected)}})
            self.assertEqual(verify(manifest, root), [])
            protected.write_text("changed\n", encoding="utf-8")
            failures = verify(manifest, root)
            self.assertEqual(len(failures), 1)
            self.assertIn("hash mismatch", failures[0])

    def test_experiment_contract_normal_and_missing_field_paths(self) -> None:
        document = {
            "exp_id": "exp_001",
            "base_commit": "a" * 40,
            "hypothesis": "one change",
            "single_variable": "loss=bpr",
            "allowed_files": ["src/training/bpr.py"],
            "forbidden_files": ["starter/evaluate.py"],
            "data_mode": "train_valid_only",
            "seeds": [0, 1],
            "smoke_batches": 5,
            "max_minutes": 120,
            "success": {"metric": "primary", "split": "valid", "min_delta": 0.002},
            "status": "PROPOSED",
        }
        validate_contract("experiment-spec", document)
        del document["hypothesis"]
        with self.assertRaisesRegex(ValidationError, "hypothesis"):
            validate_contract("experiment-spec", document)

    def test_other_four_contract_shapes(self) -> None:
        sha = "b" * 40
        documents = {
            "feature-proposal": {
                "exp_id": "exp_002", "raw_columns": ["date"], "time_boundary": "strictly before row",
                "train_only_statistics": True, "missing_values": "UNK", "dimension": 1,
                "leakage_checks": ["cutoff"], "expected_impact": "better ranking", "code_commit": sha,
            },
            "model-proposal": {
                "exp_id": "exp_002", "objective": "BPR", "sampling_unit": "user",
                "inputs": ["features"], "outputs": ["score"], "hyperparameters": {"lr": 0.001},
                "resource_estimate": {"minutes": 10}, "failure_conditions": ["NaN"],
                "fallback": "FM", "code_commit": sha,
            },
            "run-manifest": {
                "exp_id": "exp_002", "commit": sha, "dirty": False, "config_hash": "c" * 64,
                "data_hash": "d" * 64, "seed": 0, "started_at": "2026-08-29T00:00:00Z",
                "ended_at": "2026-08-29T00:01:00Z", "exit_code": 0,
                "checkpoint_hash": "e" * 64, "prediction_hash": "f" * 64,
                "log_path": "run.log", "manual_intervention": False,
                "command": ["python", "tools/run_experiment.py"],
            },
            "metrics": {
                "exp_id": "exp_002", "commit": sha,
                "valid": {"GAUC": 0.6, "nDCG@5": 0.5, "primary": 0.55},
                "baseline_delta": 0.01, "seed_summary": {"mean": 0.55, "std": 0.0},
                "prediction_checks": "PASS", "protected_hashes": {}, "compliance": "PASS",
                "recommendation": "ACCEPT",
            },
        }
        for contract_type, document in documents.items():
            with self.subTest(contract_type=contract_type):
                validate_contract(contract_type, document)


if __name__ == "__main__":
    unittest.main()
