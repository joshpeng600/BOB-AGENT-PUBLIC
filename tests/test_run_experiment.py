from __future__ import annotations

import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import numpy as np

from tests.helpers import LOG_HEADER, make_dataset, write_csv
from tools.common import ValidationError, write_json
from tools.run_experiment import (
    TransientInfrastructureError,
    _execute_with_retry,
    _settings,
    execute,
    main,
)
from tools.validate_contract import validate_artifact_files, validate_contract
from tools.validate_predictions import validate


COMMIT_SHA = "a" * 40


def candidate_config() -> dict[str, object]:
    return {
        "status": "candidate_not_validated",
        "model": {
            "name": "factorization_machine",
            "embedding_dim": 4,
            "learning_rate": 0.01,
            "l2": 0.000001,
        },
        "objective": {
            "name": "same_user_bpr",
            "negatives_per_positive": 1,
        },
        "training": {
            "seed": 0,
            "batch_size": 2,
            "epochs": 2,
            "patience": 1,
            "max_batches": None,
        },
        "data_mode": "train_valid_only",
    }


def pointwise_config() -> dict[str, object]:
    config = candidate_config()
    config["objective"] = {"name": "pointwise_binary_cross_entropy"}
    return config


def approved_spec(candidate: Path, baseline: Path) -> dict[str, object]:
    return {
        "schema_version": 1,
        "contract_type": "experiment_spec",
        "experiment_id": "exp_smoke",
        "author_role": "A",
        "created_at_utc": "2026-08-30T00:00:00Z",
        "approved_against_commit_sha": COMMIT_SHA,
        "status": "APPROVED_FOR_IMPLEMENTATION",
        "change_type": "loss_only",
        "objective": "same_user_bpr",
        "hypothesis": "same-user BPR improves within-user ranking",
        "scope": {"single_variable": "objective"},
        "task": {
            "ranking_scope": "within_user",
            "label": "long_view",
            "training_splits": ["train", "valid"],
            "maximum_development_date": 20220428,
            "evaluation_split": "valid",
            "primary_definition": "mean(GAUC,nDCG@5)",
            "test_access_allowed": False,
        },
        "baseline": {
            "baseline_experiment_id": "baseline_fm",
            "approved_config": str(baseline),
        },
        "implementation_config": str(candidate),
        "role_deliverables": {"B": ["run"]},
        "run_command": ["python", "tools/run_experiment.py"],
        "max_runtime_seconds": 60,
        "automatic_repair_attempts": 1,
    }


def make_pair_dataset(root: Path) -> Path:
    make_dataset(root)
    write_csv(
        root / "log_standard_4_08_to_4_21_pure.csv",
        LOG_HEADER,
        [
            [20220408, "u1", "v1", 1, 1000, 1],
            [20220409, "u1", "v2", 1, 2000, 0],
            [20220410, "u2", "v1", 1, 1000, 1],
            [20220411, "u2", "v2", 1, 2000, 0],
        ],
    )
    return root


class RunExperimentTests(unittest.TestCase):
    def test_repository_spec_routes_candidate_and_baseline_on_synthetic_data(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            data_dir = make_pair_dataset(base / "data")
            for variant, relative_config, expected_objective in (
                ("candidate", "configs/candidates/bpr_fm.json", "same_user_bpr"),
                ("baseline", "configs/approved/baseline_fm.json", "pointwise_binary_cross_entropy"),
            ):
                with self.subTest(variant=variant):
                    output_dir = base / variant
                    output_dir.mkdir()
                    result = execute(
                        repo_root / "experiments/exp_001.json",
                        repo_root / relative_config,
                        data_dir,
                        output_dir,
                        seed=0,
                        max_batches=1,
                        mode="valid-only",
                        repo_root=repo_root,
                    )
                    self.assertEqual(result["run_variant"], variant)
                    self.assertEqual(result["objective"], expected_objective)
                    self.assertTrue((output_dir / "valid_predictions.csv").is_file())

    def test_bpr_synthetic_smoke_writes_canonical_complete_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            data_dir = make_pair_dataset(base / "data")
            output_dir = base / "run"
            candidate_path = base / "candidate.json"
            baseline_path = base / "baseline.json"
            spec_path = base / "experiment.json"
            write_json(candidate_path, candidate_config())
            write_json(baseline_path, pointwise_config())
            write_json(spec_path, approved_spec(candidate_path, baseline_path))
            argv = [
                "run_experiment.py",
                "--experiment-spec", str(spec_path),
                "--config", str(candidate_path),
                "--data-dir", str(data_dir),
                "--output-dir", str(output_dir),
                "--seed", "0",
                "--max-batches", "1",
                "--mode", "valid-only",
            ]
            with (
                patch.object(sys, "argv", argv),
                patch("tools.run_experiment._git_state", side_effect=[(COMMIT_SHA, True)] * 2),
                patch("tools.run_experiment._git_is_ancestor", return_value=True),
                redirect_stdout(StringIO()),
            ):
                self.assertEqual(main(), 0)

            manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "completed")
            self.assertEqual(manifest["experiment_id"], "exp_smoke")
            self.assertEqual(manifest["commit_sha"], COMMIT_SHA)
            self.assertEqual(manifest["executor_role"], "B")
            self.assertEqual(manifest["objective"], "same_user_bpr")
            self.assertEqual(manifest["retry_count"], 0)
            self.assertFalse(manifest["test_access"])
            self.assertGreater(manifest["pair_coverage"]["pair_count"], 0)
            self.assertEqual(len(manifest["commands"]), 1)
            self.assertEqual(
                {artifact["path"] for artifact in manifest["artifacts"]},
                {
                    "valid_predictions.csv",
                    "checkpoint.npz",
                    "resolved_config.json",
                    "training_history.json",
                    "runner_metrics.json",
                },
            )
            validate_contract("run-manifest", manifest)
            validate_artifact_files(manifest, output_dir)
            self.assertEqual(validate(output_dir / "valid_predictions.csv", data_dir, "valid")["rows"], 2)
            with np.load(output_dir / "checkpoint.npz", allow_pickle=False) as checkpoint:
                self.assertTrue({"mV", "vV", "mW", "vW", "t"}.issubset(checkpoint.files))

            (output_dir / "resolved_config.json").write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValidationError, "artifact hash mismatch"):
                validate_artifact_files(manifest, output_dir)

    def test_dirty_worktree_fails_closed_before_training_and_writes_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            output_dir = base / "run"
            argv = [
                "run_experiment.py",
                "--experiment-spec", str(base / "unused_spec.json"),
                "--config", str(base / "unused_config.json"),
                "--data-dir", str(base / "unused_data"),
                "--output-dir", str(output_dir),
            ]
            with (
                patch.object(sys, "argv", argv),
                patch("tools.run_experiment._git_state", return_value=(COMMIT_SHA, False)),
                patch("tools.run_experiment.execute") as execute_mock,
                redirect_stderr(StringIO()),
            ):
                self.assertEqual(main(), 1)
            execute_mock.assert_not_called()
            manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "failed")
            self.assertIn("worktree must be clean", manifest["error"])
            validate_contract("run-manifest", manifest)

    def test_artifact_hash_failure_cannot_leave_a_completed_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            data_dir = make_pair_dataset(base / "data")
            output_dir = base / "run"
            candidate_path = base / "candidate.json"
            baseline_path = base / "baseline.json"
            spec_path = base / "experiment.json"
            write_json(candidate_path, candidate_config())
            write_json(baseline_path, pointwise_config())
            write_json(spec_path, approved_spec(candidate_path, baseline_path))
            argv = [
                "run_experiment.py",
                "--experiment-spec", str(spec_path),
                "--config", str(candidate_path),
                "--data-dir", str(data_dir),
                "--output-dir", str(output_dir),
                "--seed", "0",
                "--max-batches", "1",
                "--mode", "valid-only",
            ]
            with (
                patch.object(sys, "argv", argv),
                patch("tools.run_experiment._git_state", side_effect=[(COMMIT_SHA, True)] * 2),
                patch("tools.run_experiment._git_is_ancestor", return_value=True),
                patch(
                    "tools.run_experiment.validate_artifact_files",
                    side_effect=ValidationError("artifact hash mismatch"),
                ),
                redirect_stderr(StringIO()),
            ):
                self.assertEqual(main(), 1)

            manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "failed")
            self.assertEqual(manifest["exit_code"], 1)
            self.assertIn("artifact hash mismatch", manifest["error"])

    def test_executed_config_drift_cannot_leave_a_completed_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            data_dir = make_pair_dataset(base / "data")
            output_dir = base / "run"
            candidate_path = base / "candidate.json"
            baseline_path = base / "baseline.json"
            spec_path = base / "experiment.json"
            write_json(candidate_path, candidate_config())
            write_json(baseline_path, pointwise_config())
            write_json(spec_path, approved_spec(candidate_path, baseline_path))
            argv = [
                "run_experiment.py",
                "--experiment-spec", str(spec_path),
                "--config", str(candidate_path),
                "--data-dir", str(data_dir),
                "--output-dir", str(output_dir),
                "--seed", "0",
                "--max-batches", "1",
                "--mode", "valid-only",
            ]
            with (
                patch.object(sys, "argv", argv),
                patch(
                    "tools.run_experiment._git_state",
                    return_value=(COMMIT_SHA, True),
                ),
                patch("tools.run_experiment._git_is_ancestor", return_value=True),
                patch(
                    "tools.run_experiment.execute",
                    return_value={"resolved_config": {"drifted": True}},
                ),
                redirect_stderr(StringIO()),
            ):
                self.assertEqual(main(), 1)

            manifest = json.loads(
                (output_dir / "run_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["status"], "failed")
            self.assertEqual(manifest["exit_code"], 1)
            self.assertEqual(manifest["artifacts"], [])
            self.assertIn("executed resolved config", manifest["error"])

    def test_only_explicit_transient_error_is_retried_once(self) -> None:
        calls = 0

        def transient_then_success() -> dict[str, object]:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise TransientInfrastructureError("temporary filesystem issue")
            return {"ok": True}

        result, retries = _execute_with_retry(transient_then_success, 1)
        self.assertEqual(result, {"ok": True})
        self.assertEqual((calls, retries), (2, 1))

        with self.assertRaisesRegex(ValidationError, "contract error"):
            _execute_with_retry(lambda: (_ for _ in ()).throw(ValidationError("contract error")), 1)

    def test_canonical_config_and_cli_overrides_fail_closed(self) -> None:
        resolved = _settings(candidate_config(), seed=0, max_batches=1)
        self.assertEqual(resolved["embedding_dim"], 4)
        self.assertEqual(resolved["max_batches"], 1)
        legacy = candidate_config()
        legacy["training"] = {"seed": 0, "batch": 2, "epochs": 1, "patience": 1}
        with self.assertRaisesRegex(ValidationError, "legacy runner field"):
            _settings(legacy)
        with self.assertRaisesRegex(ValidationError, "does not match"):
            _settings(candidate_config(), seed=7)


if __name__ == "__main__":
    unittest.main()
