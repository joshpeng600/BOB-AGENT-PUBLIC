from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from tools.common import ValidationError, sha256_file, write_json
from tools.validate_contract import validate_contract
from tools.verify_protected_files import verify


SHA = "b" * 40
DIGEST = "c" * 64


def canonical_documents() -> dict[str, dict[str, object]]:
    common_proposal = {
        "schema_version": 1,
        "experiment_id": "exp_002",
        "proposal_id": "proposal-1",
        "created_at_utc": "2026-08-30T00:00:00Z",
        "approved_against_commit_sha": SHA,
        "implementation_commit_sha": None,
        "name": "proposal",
        "hypothesis": "one controlled change may improve ranking",
        "status": "PROPOSED",
    }
    return {
        "feature-proposal": {
            **common_proposal,
            "contract_type": "feature_proposal",
            "author_role": "C",
            "inputs": ["past rows"],
            "transform": "train-fitted count",
            "leakage_review": {
                "uses_future_information": False,
                "uses_test_information": False,
            },
            "ablation_plan": "compare with unchanged baseline",
        },
        "model-proposal": {
            **common_proposal,
            "contract_type": "model_proposal",
            "author_role": "D",
            "model_family": "factorization_machine",
            "objective": {"name": "same_user_bpr"},
            "sampling": {"unit": "same_user"},
            "input_output": {"input": "features", "output": "score"},
            "hyperparameters": {"learning_rate": 0.001},
            "dependency_changes": [],
            "resource_estimate": {"seconds": 60},
            "failure_conditions": ["NaN"],
            "fallback": "pointwise baseline",
            "validation_claim": "none until E evaluates",
        },
        "run-manifest": {
            "schema_version": 1,
            "contract_type": "run_manifest",
            "experiment_id": "exp_002",
            "run_id": "run-1",
            "commit_sha": SHA,
            "worktree_clean": True,
            "started_at_utc": "2026-08-30T00:00:00Z",
            "finished_at_utc": "2026-08-30T00:01:00Z",
            "executor_role": "B",
            "experiment_spec_path": "experiments/exp_002.json",
            "config_path": "configs/candidates/example.json",
            "config_hash": DIGEST,
            "config": {},
            "data": {"split": "valid", "hash": DIGEST},
            "data_hash": DIGEST,
            "seed": 0,
            "dev_max_date": 20220428,
            "environment": {"python": "3.13"},
            "protected_hashes": {"starter/evaluate.py": DIGEST},
            "commands": ["python tools/run_experiment.py --mode valid-only"],
            "prediction_hash": DIGEST,
            "checkpoint_hash": DIGEST,
            "artifacts": [
                {"path": path, "sha256": DIGEST}
                for path in (
                    "valid_predictions.csv",
                    "checkpoint.npz",
                    "resolved_config.json",
                    "training_history.json",
                    "runner_metrics.json",
                )
            ],
            "status": "completed",
        },
        "metrics": {
            "schema_version": 1,
            "contract_type": "metrics",
            "experiment_id": "exp_002",
            "run_id": "run-1",
            "baseline_experiment_id": "baseline_fm",
            "commit_sha": SHA,
            "worktree_clean": True,
            "evaluator_role": "E",
            "status": "completed",
            "hypothesis": "same-user BPR improves ranking",
            "code_diff": "objective only",
            "split": "valid",
            "metrics": {"GAUC": 0.6, "nDCG@5": 0.5, "primary": 0.55},
            "errors": [],
            "recovery": None,
            "manual_interventions": 0,
            "tokens": 0,
            "wall_time_seconds": 1,
            "iterations": 1,
            "gpu_hours": 0,
            "config": {},
            "data": {"split": "valid"},
            "seed": 0,
            "protected_hashes": {"starter/evaluate.py": DIGEST},
            "artifact_manifest_path": "artifacts/run_manifest.json",
        },
        "decision-request": {
            "schema_version": 1,
            "contract_type": "decision_request",
            "experiment_id": "exp_002",
            "request_id": "decision-1",
            "requested_at_utc": "2026-08-30T00:00:00Z",
            "requested_by_role": "B",
            "approved_against_commit_sha": SHA,
            "trigger": "contract ambiguity",
            "summary": "human choice is required",
            "evidence_paths": [],
            "options": [],
            "automation_paused": True,
            "status": "pending_human",
        },
        "final-approval": {
            "schema_version": 1,
            "contract_type": "final_approval",
            "experiment_id": "exp_002",
            "commit_sha": SHA,
            "approved": True,
            "approved_by": "human-owner",
            "approved_at": "2026-08-30T00:00:00Z",
            "protected_hashes": {"starter/evaluate.py": DIGEST},
        },
    }


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

    def test_current_experiment_contract_and_missing_field_paths(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        document = json.loads((repo_root / "experiments" / "exp_001.json").read_text(encoding="utf-8"))
        validate_contract("experiment-spec", document)
        del document["hypothesis"]
        with self.assertRaisesRegex(ValidationError, "hypothesis"):
            validate_contract("experiment-spec", document)

    def test_all_handoff_contract_shapes_are_canonical(self) -> None:
        for contract_type, document in canonical_documents().items():
            with self.subTest(contract_type=contract_type):
                validate_contract(contract_type, document)

    def test_legacy_alias_and_test_request_are_rejected_recursively(self) -> None:
        manifest = deepcopy(canonical_documents()["run-manifest"])
        manifest["config"] = {"nested": {"commit": SHA}}
        with self.assertRaisesRegex(ValidationError, "forbidden legacy field"):
            validate_contract("run-manifest", manifest)

        manifest = deepcopy(canonical_documents()["run-manifest"])
        manifest["config"] = {"evaluation_split": "test"}
        with self.assertRaisesRegex(ValidationError, "test split denied"):
            validate_contract("run-manifest", manifest)

    def test_completed_run_requires_a_complete_unique_safe_artifact_inventory(self) -> None:
        manifest = deepcopy(canonical_documents()["run-manifest"])
        manifest["artifacts"] = manifest["artifacts"][:-1]
        with self.assertRaisesRegex(ValidationError, "missing required artifacts"):
            validate_contract("run-manifest", manifest)

        manifest = deepcopy(canonical_documents()["run-manifest"])
        manifest["artifacts"].append(deepcopy(manifest["artifacts"][0]))
        with self.assertRaisesRegex(ValidationError, "duplicate artifact path"):
            validate_contract("run-manifest", manifest)

        manifest = deepcopy(canonical_documents()["run-manifest"])
        manifest["artifacts"][0]["path"] = "../valid_predictions.csv"
        with self.assertRaisesRegex(ValidationError, "normalized relative path"):
            validate_contract("run-manifest", manifest)

        for unsafe_path in ("C:/outside/checkpoint.npz", "C:\\outside\\checkpoint.npz"):
            with self.subTest(unsafe_path=unsafe_path):
                manifest = deepcopy(canonical_documents()["run-manifest"])
                manifest["artifacts"][1]["path"] = unsafe_path
                with self.assertRaisesRegex(ValidationError, "normalized relative path"):
                    validate_contract("run-manifest", manifest)


if __name__ == "__main__":
    unittest.main()
