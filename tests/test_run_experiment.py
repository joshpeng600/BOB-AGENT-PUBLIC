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
from tools.audit_run import audit_manifest
from tools.common import (
    OFFICIAL_LOG_FILES,
    REQUIRED_STATIC_FILES,
    ValidationError,
    sha256_file,
    write_json,
)
from tools.project_security import expected_protected_hashes
from tools.run_experiment import (
    TransientInfrastructureError,
    _capture_data_snapshot,
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
    config.update(
        schema_version=1,
        contract_type="approved_config",
        experiment_id="baseline_fm",
        approved_against_commit_sha=COMMIT_SHA,
        status="APPROVED",
    )
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


def write_dataset_manifest(root: Path) -> None:
    names = (*OFFICIAL_LOG_FILES, *REQUIRED_STATIC_FILES)
    write_json(
        root / "dataset_manifest.json",
        {
            "format_version": 1,
            "test_rows": 0,
            "files": {
                name: {"sha256": sha256_file(root / name)}
                for name in names
            },
        },
    )


def make_runner_fixture(base: Path, *, with_manifest: bool = False) -> dict[str, Path]:
    data_dir = make_pair_dataset(base / "data")
    if with_manifest:
        write_dataset_manifest(data_dir)
    candidate_path = base / "candidate.json"
    baseline_path = base / "baseline.json"
    spec_path = base / "experiment.json"
    write_json(candidate_path, candidate_config())
    write_json(baseline_path, pointwise_config())
    write_json(spec_path, approved_spec(candidate_path, baseline_path))
    return {
        "data": data_dir,
        "output": base / "run",
        "candidate": candidate_path,
        "baseline": baseline_path,
        "spec": spec_path,
    }


def runner_argv(
    paths: dict[str, Path], *, synthetic_smoke: bool = True,
) -> list[str]:
    argv = [
        "run_experiment.py",
        "--experiment-spec", str(paths["spec"]),
        "--config", str(paths["candidate"]),
        "--data-dir", str(paths["data"]),
        "--output-dir", str(paths["output"]),
        "--seed", "0",
        "--mode", "valid-only",
    ]
    if synthetic_smoke:
        argv.extend(("--max-batches", "1", "--synthetic-smoke"))
    return argv


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
                        synthetic_smoke=True,
                    )
                    self.assertEqual(result["run_variant"], variant)
                    self.assertEqual(result["objective"], expected_objective)
                    self.assertTrue((output_dir / "valid_predictions.csv").is_file())

    def test_bpr_synthetic_smoke_writes_canonical_complete_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo_root = Path(__file__).resolve().parents[1]
            data_dir = make_pair_dataset(base / "data")
            output_dir = base / "run"
            candidate_path = repo_root / "configs" / "candidates" / "bpr_fm.json"
            spec_path = repo_root / "experiments" / "exp_001.json"
            argv = [
                "run_experiment.py",
                "--experiment-spec", str(spec_path),
                "--config", str(candidate_path),
                "--data-dir", str(data_dir),
                "--output-dir", str(output_dir),
                "--seed", "0",
                "--max-batches", "1",
                "--mode", "valid-only",
                "--synthetic-smoke",
            ]
            with (
                patch.object(sys, "argv", argv),
                patch("tools.run_experiment._git_state", side_effect=[(COMMIT_SHA, True)] * 2),
                patch("tools.run_experiment._git_is_ancestor", return_value=True),
                redirect_stdout(StringIO()),
            ):
                self.assertEqual(main(), 0)

            manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "synthetic_smoke")
            self.assertEqual(manifest["evidence_tier"], "synthetic_only")
            self.assertEqual(manifest["experiment_id"], "exp_001")
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
            validate_artifact_files(manifest, output_dir, formal_evidence=False)
            self.assertEqual(validate(output_dir / "valid_predictions.csv", data_dir, "valid")["rows"], 2)
            with np.load(output_dir / "checkpoint.npz", allow_pickle=False) as checkpoint:
                self.assertTrue({"mV", "vV", "mW", "vW", "t"}.issubset(checkpoint.files))

            (output_dir / "resolved_config.json").write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValidationError, "artifact hash mismatch"):
                validate_artifact_files(manifest, output_dir, formal_evidence=False)

    def test_repository_inputs_produce_an_auditable_completed_package(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            data_dir = make_pair_dataset(base / "data")
            output_dir = base / "run"
            paths = {
                "spec": repo_root / "experiments" / "exp_001.json",
                "candidate": repo_root / "configs" / "candidates" / "bpr_fm.json",
                "data": data_dir,
                "output": output_dir,
            }
            with (
                patch.object(sys, "argv", runner_argv(paths, synthetic_smoke=False)),
                patch(
                    "tools.run_experiment._git_state",
                    side_effect=[(COMMIT_SHA, True)] * 2,
                ),
                patch("tools.run_experiment._git_is_ancestor", return_value=True),
                redirect_stdout(StringIO()),
            ):
                self.assertEqual(main(), 0)

            protected = expected_protected_hashes()
            with (
                patch("tools.audit_run.verify_protected_files", return_value=protected),
                patch("tools.audit_run.expected_protected_hashes", return_value=protected),
                patch("tools.audit_run.git_head", return_value=COMMIT_SHA),
                patch("tools.audit_run.git_is_dirty", return_value=False),
                patch("tools.audit_run._git_is_ancestor", return_value=True),
            ):
                audited = audit_manifest(output_dir / "run_manifest.json")
            self.assertEqual(audited["status"], "completed")

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

    def test_formal_main_rejects_repository_external_spec(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_runner_fixture(Path(tmp))
            with (
                patch.object(sys, "argv", runner_argv(paths)),
                patch("tools.run_experiment._git_state", return_value=(COMMIT_SHA, True)),
                patch("tools.run_experiment.execute") as execute_mock,
                redirect_stderr(StringIO()),
            ):
                self.assertEqual(main(), 1)
            execute_mock.assert_not_called()
            manifest = json.loads(
                (paths["output"] / "run_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["status"], "failed")
            self.assertIn("experiment spec must be inside", manifest["error"])

    def test_baseline_approval_ancestry_fails_before_data_access(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_runner_fixture(Path(tmp))
            argv = runner_argv(paths)
            argv[argv.index(str(paths["candidate"]))] = str(paths["baseline"])
            with (
                patch.object(sys, "argv", argv),
                patch("tools.run_experiment._require_repository_input"),
                patch("tools.run_experiment._git_state", return_value=(COMMIT_SHA, True)),
                patch(
                    "tools.run_experiment._git_is_ancestor",
                    side_effect=[True, False],
                ),
                patch("tools.run_experiment._capture_data_snapshot") as capture,
                patch("tools.run_experiment.execute") as execute_mock,
                redirect_stderr(StringIO()),
            ):
                self.assertEqual(main(), 1)
            capture.assert_not_called()
            execute_mock.assert_not_called()
            manifest = json.loads(
                (paths["output"] / "run_manifest.json").read_text(encoding="utf-8")
            )
            self.assertIn("baseline approved_against_commit_sha", manifest["error"])

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
                "--synthetic-smoke",
            ]
            with (
                patch.object(sys, "argv", argv),
                patch("tools.run_experiment._require_repository_input"),
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
                "--synthetic-smoke",
            ]
            with (
                patch.object(sys, "argv", argv),
                patch("tools.run_experiment._require_repository_input"),
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

    def test_interrupted_artifact_validation_cannot_leave_completed_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_runner_fixture(Path(tmp))
            with (
                patch.object(sys, "argv", runner_argv(paths)),
                patch("tools.run_experiment._require_repository_input"),
                patch(
                    "tools.run_experiment._git_state",
                    side_effect=[(COMMIT_SHA, True)] * 2,
                ),
                patch("tools.run_experiment._git_is_ancestor", return_value=True),
                patch(
                    "tools.run_experiment.validate_artifact_files",
                    side_effect=KeyboardInterrupt(),
                ),
            ):
                with self.assertRaises(KeyboardInterrupt):
                    main()

            manifest = json.loads(
                (paths["output"] / "run_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["status"], "failed")
            self.assertEqual(manifest["exit_code"], 1)
            self.assertEqual(manifest["artifacts"], [])
            self.assertIn("KeyboardInterrupt", manifest["error"])

    def test_dataset_manifest_file_hash_mismatch_fails_before_execute(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_runner_fixture(Path(tmp), with_manifest=True)
            train = paths["data"] / OFFICIAL_LOG_FILES[0]
            train.write_text(
                train.read_text(encoding="utf-8").replace("u1,v1", "u9,v1", 1),
                encoding="utf-8",
            )
            with (
                patch.object(sys, "argv", runner_argv(paths)),
                patch("tools.run_experiment._require_repository_input"),
                patch("tools.run_experiment._git_state", return_value=(COMMIT_SHA, True)),
                patch("tools.run_experiment._git_is_ancestor", return_value=True),
                patch("tools.run_experiment.execute") as execute_mock,
                redirect_stderr(StringIO()),
            ):
                self.assertEqual(main(), 1)
            execute_mock.assert_not_called()
            manifest = json.loads(
                (paths["output"] / "run_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["status"], "failed")
            self.assertIn("dataset source hash mismatch", manifest["error"])

    def test_dataset_manifest_validates_every_declared_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = make_pair_dataset(Path(tmp) / "data")
            extra = data_dir / "user_features_pure.csv"
            extra.write_text("user_id,feature\nu1,1\n", encoding="utf-8")
            write_dataset_manifest(data_dir)
            manifest = json.loads(
                (data_dir / "dataset_manifest.json").read_text(encoding="utf-8")
            )
            manifest["files"][extra.name] = {"sha256": sha256_file(extra)}
            write_json(data_dir / "dataset_manifest.json", manifest)
            extra.write_text("user_id,feature\nu1,999\n", encoding="utf-8")
            with self.assertRaisesRegex(ValidationError, "dataset source hash mismatch"):
                _capture_data_snapshot(data_dir)

    def test_experiment_spec_drift_during_execute_cannot_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_runner_fixture(Path(tmp))

            def drift_spec(*_args: object, **_kwargs: object) -> dict[str, object]:
                spec = json.loads(paths["spec"].read_text(encoding="utf-8"))
                spec["max_runtime_seconds"] = 59
                write_json(paths["spec"], spec)
                return {}

            with (
                patch.object(sys, "argv", runner_argv(paths)),
                patch("tools.run_experiment._require_repository_input"),
                patch("tools.run_experiment._git_state", return_value=(COMMIT_SHA, True)),
                patch("tools.run_experiment._git_is_ancestor", return_value=True),
                patch("tools.run_experiment.execute", side_effect=drift_spec),
                redirect_stderr(StringIO()),
            ):
                self.assertEqual(main(), 1)
            manifest = json.loads(
                (paths["output"] / "run_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["status"], "failed")
            self.assertEqual(manifest["exit_code"], 1)
            self.assertIn("experiment spec changed", manifest["error"])

    def test_approved_config_drift_during_execute_cannot_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_runner_fixture(Path(tmp))

            def drift_config(*_args: object, **_kwargs: object) -> dict[str, object]:
                config = json.loads(paths["candidate"].read_text(encoding="utf-8"))
                config["model"]["learning_rate"] = 0.02
                write_json(paths["candidate"], config)
                return {}

            with (
                patch.object(sys, "argv", runner_argv(paths)),
                patch("tools.run_experiment._require_repository_input"),
                patch("tools.run_experiment._git_state", return_value=(COMMIT_SHA, True)),
                patch("tools.run_experiment._git_is_ancestor", return_value=True),
                patch("tools.run_experiment.execute", side_effect=drift_config),
                redirect_stderr(StringIO()),
            ):
                self.assertEqual(main(), 1)
            manifest = json.loads(
                (paths["output"] / "run_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["status"], "failed")
            self.assertEqual(manifest["exit_code"], 1)
            self.assertIn("approved config changed", manifest["error"])

    def test_data_drift_during_execute_cannot_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_runner_fixture(Path(tmp), with_manifest=True)
            train = paths["data"] / OFFICIAL_LOG_FILES[0]

            def drift_data(*_args: object, **_kwargs: object) -> dict[str, object]:
                train.write_text(
                    train.read_text(encoding="utf-8").replace("u1,v1", "u9,v1", 1),
                    encoding="utf-8",
                )
                return {}

            with (
                patch.object(sys, "argv", runner_argv(paths)),
                patch("tools.run_experiment._require_repository_input"),
                patch("tools.run_experiment._git_state", return_value=(COMMIT_SHA, True)),
                patch("tools.run_experiment._git_is_ancestor", return_value=True),
                patch("tools.run_experiment.execute", side_effect=drift_data),
                redirect_stderr(StringIO()),
            ):
                self.assertEqual(main(), 1)
            manifest = json.loads(
                (paths["output"] / "run_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["status"], "failed")
            self.assertEqual(manifest["exit_code"], 1)
            self.assertIn("dataset source hash mismatch", manifest["error"])

    def test_execute_uses_snapshot_when_source_is_swapped_and_restored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_runner_fixture(Path(tmp), with_manifest=True)
            source = paths["data"] / OFFICIAL_LOG_FILES[0]
            original = source.read_bytes()
            expected = _capture_data_snapshot(paths["data"])

            def observe_bound_snapshot(
                _spec: dict[str, object], _config: dict[str, object], _variant: str,
                snapshot_dir: Path, *_args: object,
            ) -> dict[str, object]:
                source.write_bytes(b"malicious-but-temporary\n")
                try:
                    self.assertNotEqual(source.read_bytes(), original)
                    self.assertEqual(
                        (snapshot_dir / OFFICIAL_LOG_FILES[0]).read_bytes(), original
                    )
                    return {"snapshot_bound": True}
                finally:
                    source.write_bytes(original)

            with patch(
                "tools.run_experiment._execute_bound_snapshot",
                side_effect=observe_bound_snapshot,
            ):
                result = execute(
                    paths["spec"], paths["candidate"], paths["data"],
                    paths["output"], seed=0, max_batches=1, mode="valid-only",
                    repo_root=Path(tmp), expected_data_snapshot=expected,
                    synthetic_smoke=True,
                )
            self.assertEqual(result, {"snapshot_bound": True})
            self.assertEqual(source.read_bytes(), original)

    def test_execute_records_configured_effective_max_batches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            paths = make_runner_fixture(base)
            config = candidate_config()
            config["training"]["max_batches"] = 1
            write_json(paths["candidate"], config)
            paths["output"].mkdir()
            result = execute(
                paths["spec"], paths["candidate"], paths["data"], paths["output"],
                seed=0, max_batches=None, mode="valid-only", repo_root=base,
            )
            self.assertEqual(result["resolved_config"]["resolved_run"]["max_batches"], 1)
            self.assertEqual(result["batches_seen"], 1)
            history = json.loads(result["history_path"].read_text(encoding="utf-8"))
            self.assertEqual(len(history), 1)

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
        resolved = _settings(
            candidate_config(), seed=0, max_batches=1, synthetic_smoke=True
        )
        self.assertEqual(resolved["embedding_dim"], 4)
        self.assertEqual(resolved["max_batches"], 1)
        configured_limit = candidate_config()
        configured_limit["training"]["max_batches"] = 2
        self.assertEqual(
            _settings(configured_limit, seed=0, max_batches=None)["max_batches"],
            2,
        )
        legacy = candidate_config()
        legacy["training"] = {"seed": 0, "batch": 2, "epochs": 1, "patience": 1}
        with self.assertRaisesRegex(ValidationError, "legacy runner field"):
            _settings(legacy)
        with self.assertRaisesRegex(ValidationError, "does not match"):
            _settings(candidate_config(), seed=7)
        with self.assertRaisesRegex(ValidationError, "formal max-batches"):
            _settings(candidate_config(), seed=0, max_batches=1)

    def test_formal_cli_truncation_is_rejected_before_data_access(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_runner_fixture(Path(tmp))
            argv = runner_argv(paths)
            argv.remove("--synthetic-smoke")
            with (
                patch.object(sys, "argv", argv),
                patch("tools.run_experiment._require_repository_input"),
                patch("tools.run_experiment._git_state", return_value=(COMMIT_SHA, True)),
                patch("tools.run_experiment._git_is_ancestor", return_value=True),
                patch("tools.run_experiment._capture_data_snapshot") as capture,
                redirect_stderr(StringIO()),
            ):
                self.assertEqual(main(), 1)
            capture.assert_not_called()
            manifest = json.loads(
                (paths["output"] / "run_manifest.json").read_text(encoding="utf-8")
            )
            self.assertIn("formal max-batches", manifest["error"])
            self.assertEqual(manifest["status"], "failed")

    def test_invalid_mode_and_approved_identity_fail_before_data_access(self) -> None:
        spec = approved_spec(Path("candidate.json"), Path("baseline.json"))
        config = candidate_config()
        with patch("tools.run_experiment._capture_data_snapshot") as capture:
            with self.assertRaisesRegex(ValidationError, "valid-only"):
                execute(
                    Path("unused-spec.json"), Path("unused-config.json"),
                    Path("unused-data"), Path("unused-output"), seed=0,
                    max_batches=1, mode="experiment",
                    approved_inputs=(spec, config, "candidate"),
                    synthetic_smoke=True,
                )
            capture.assert_not_called()

        spec["author_role"] = "E"
        with patch("tools.run_experiment._capture_data_snapshot") as capture:
            with self.assertRaisesRegex(ValidationError, "author_role"):
                execute(
                    Path("unused-spec.json"), Path("unused-config.json"),
                    Path("unused-data"), Path("unused-output"), seed=0,
                    max_batches=1, mode="valid-only",
                    approved_inputs=(spec, config, "candidate"),
                    synthetic_smoke=True,
                )
            capture.assert_not_called()


if __name__ == "__main__":
    unittest.main()
