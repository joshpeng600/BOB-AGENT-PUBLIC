from __future__ import annotations

from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.common import ValidationError, sha256_file, stable_json_hash, write_json
from tools.audit_run import (
    _git_is_ancestor,
    audit_manifest,
    is_test_scoring_command,
    validate_manifest_record,
    verify_approved_repository_inputs,
)
from tools.final_approval import validate_approval_record
from tools.project_security import SecurityError
from tools.validate_contract import (
    _assert_artifact_binding,
    _read_open_artifact,
    validate_approved_run_semantics,
    validate_approved_run_route,
)


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.commit = "a" * 40
        self.hashes = {"starter/evaluate.py": "b" * 64}
        self.digest = "c" * 64
        self.repo_root = Path(__file__).resolve().parents[1]
        self.spec_path = self.repo_root / "experiments" / "exp_001.json"
        self.config_path = self.repo_root / "configs" / "candidates" / "bpr_fm.json"
        self.spec_hash = sha256_file(self.spec_path)
        raw_config = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.config = {
            **raw_config,
            "resolved_run": {
                "experiment_id": "exp_001",
                "run_variant": "candidate",
                "seed": 0,
                "max_batches": None,
                "mode": "valid-only",
            },
        }
        self.manifest = {
            "schema_version": 1,
            "contract_type": "run_manifest",
            "experiment_id": "exp_001",
            "run_id": "run001",
            "commit_sha": self.commit,
            "worktree_clean": True,
            "started_at_utc": "2026-08-30T00:00:00Z",
            "finished_at_utc": "2026-08-30T00:01:00Z",
            "executor_role": "B",
            "experiment_spec_path": "experiments/exp_001.json",
            "experiment_spec_hash": self.spec_hash,
            "run_variant": "candidate",
            "objective": "same_user_bpr",
            "config_path": "configs/candidates/bpr_fm.json",
            "config_input_hash": sha256_file(self.config_path),
            "config_hash": stable_json_hash(self.config),
            "config": self.config,
            "mode": "valid-only",
            "max_batches": None,
            "data": {
                "dataset": "KuaiRand-Pure",
                "split": "valid",
                "hash": self.digest,
            },
            "data_hash": self.digest,
            "seed": 0,
            "dev_max_date": 20220428,
            "environment": {
                "python": "3.12.0",
                "platform": "test",
                "requirements_sha256": self.digest,
            },
            "protected_hashes": self.hashes,
            "commands": ["python3 train.py --split valid"],
            "prediction_hash": self.digest,
            "checkpoint_hash": self.digest,
            "artifacts": [
                {"path": "valid_predictions.csv", "sha256": self.digest},
                {"path": "checkpoint.npz", "sha256": self.digest},
                {"path": "resolved_config.json", "sha256": self.digest},
                {"path": "training_history.json", "sha256": self.digest},
                {"path": "runner_metrics.json", "sha256": self.digest},
            ],
            "status": "completed",
        }

    def test_accepts_complete_clean_manifest(self):
        validate_manifest_record(self.manifest, self.commit, False, self.hashes)

    def test_rejects_short_commit(self):
        self.manifest["commit_sha"] = "abc123"
        with self.assertRaises(SecurityError):
            validate_manifest_record(self.manifest, self.commit, False, self.hashes)

    def test_rejects_dirty_state(self):
        self.manifest["worktree_clean"] = False
        with self.assertRaises(SecurityError):
            validate_manifest_record(self.manifest, self.commit, False, self.hashes)
        self.manifest["worktree_clean"] = True
        with self.assertRaises(SecurityError):
            validate_manifest_record(self.manifest, self.commit, True, self.hashes)

    def test_rejects_test_leakage_date(self):
        self.manifest["dev_max_date"] = 20220429
        with self.assertRaises(SecurityError):
            validate_manifest_record(self.manifest, self.commit, False, self.hashes)

    def test_rejects_wrong_executor_role(self):
        self.manifest["executor_role"] = "E"
        with self.assertRaises(SecurityError):
            validate_manifest_record(self.manifest, self.commit, False, self.hashes)

    def test_rejects_missing_required_artifact_hashes(self):
        for field in (
            "config_input_hash", "config_hash", "data_hash", "prediction_hash",
            "checkpoint_hash",
        ):
            with self.subTest(field=field):
                value = self.manifest.pop(field)
                try:
                    with self.assertRaises(SecurityError):
                        validate_manifest_record(
                            self.manifest, self.commit, False, self.hashes
                        )
                finally:
                    self.manifest[field] = value

    def test_rejects_hashes_that_do_not_bind_recorded_content(self):
        self.manifest["config_hash"] = "d" * 64
        with self.assertRaisesRegex(SecurityError, "config_hash"):
            validate_manifest_record(self.manifest, self.commit, False, self.hashes)
        self.manifest["config_hash"] = stable_json_hash(self.config)
        self.manifest["data"]["hash"] = "d" * 64
        with self.assertRaisesRegex(SecurityError, "data.hash"):
            validate_manifest_record(self.manifest, self.commit, False, self.hashes)

    def test_rejects_legacy_aliases_at_any_depth(self):
        for field in ("exp_id", "base_commit", "commit", "frozen_commit"):
            with self.subTest(field=field):
                self.manifest["config"][field] = self.commit
                try:
                    with self.assertRaisesRegex(SecurityError, "forbidden legacy field"):
                        validate_manifest_record(
                            self.manifest, self.commit, False, self.hashes
                        )
                finally:
                    self.manifest["config"].pop(field)

    def test_rejects_changed_protected_hash(self):
        self.manifest["protected_hashes"] = {"starter/evaluate.py": "changed"}
        with self.assertRaises(SecurityError):
            validate_manifest_record(self.manifest, self.commit, False, self.hashes)

    def test_detects_test_scoring_commands(self):
        command = "python3 submit.py output.csv --score --split test"
        self.assertTrue(is_test_scoring_command(command))
        self.manifest["commands"] = [command]
        with self.assertRaises(SecurityError):
            validate_manifest_record(self.manifest, self.commit, False, self.hashes)

    def test_git_ancestry_uses_approved_then_run_commit_and_fails_closed(self):
        approved, run_commit = "a" * 40, "b" * 40
        with patch("tools.audit_run.subprocess.run") as git:
            git.return_value.returncode = 0
            self.assertTrue(_git_is_ancestor(approved, run_commit))
            self.assertEqual(
                git.call_args.args[0],
                ["git", "merge-base", "--is-ancestor", approved, run_commit],
            )
        with patch(
            "tools.audit_run.subprocess.run", side_effect=OSError("git unavailable")
        ):
            self.assertFalse(_git_is_ancestor(approved, run_commit))


class ArtifactAuditTests(unittest.TestCase):
    def setUp(self):
        AuditTests.setUp(self)

    def _write_package(self, root: Path) -> Path:
        payloads = {
            "valid_predictions.csv": b"row_id,user_id,video_id,score\n0,u1,v1,0.5\n",
            "checkpoint.npz": b"synthetic-checkpoint",
            "training_history.json": b"{}\n",
            "runner_metrics.json": b"{}\n",
        }
        for name, payload in payloads.items():
            (root / name).write_bytes(payload)
        write_json(root / "resolved_config.json", self.config)

        manifest = deepcopy(self.manifest)
        artifact_hashes = {
            path: sha256_file(root / path)
            for path in (
                "valid_predictions.csv",
                "checkpoint.npz",
                "resolved_config.json",
                "training_history.json",
                "runner_metrics.json",
            )
        }
        manifest["prediction_hash"] = artifact_hashes["valid_predictions.csv"]
        manifest["checkpoint_hash"] = artifact_hashes["checkpoint.npz"]
        manifest["artifacts"] = [
            {"path": path, "sha256": digest}
            for path, digest in artifact_hashes.items()
        ]
        manifest_path = root / "run_manifest.json"
        write_json(manifest_path, manifest)
        return manifest_path

    def _audit(
        self, manifest_path: Path, *, approved_ancestor: bool = True,
    ) -> dict[str, object]:
        with (
            patch("tools.audit_run.verify_protected_files", return_value=self.hashes),
            patch("tools.audit_run.expected_protected_hashes", return_value=self.hashes),
            patch("tools.audit_run.git_head", return_value=self.commit),
            patch("tools.audit_run.git_is_dirty", return_value=False),
            patch(
                "tools.audit_run._git_is_ancestor",
                return_value=approved_ancestor,
            ),
        ):
            return audit_manifest(manifest_path)

    def test_audit_manifest_accepts_complete_byte_bound_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = self._write_package(Path(tmp))
            self.assertEqual(self._audit(manifest_path)["status"], "completed")

    def test_audit_manifest_rejects_non_completed_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._write_package(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["status"] = "failed"
            write_json(manifest_path, manifest)
            with self.assertRaisesRegex(SecurityError, "only a completed"):
                self._audit(manifest_path)

    def test_audit_manifest_rejects_tampered_and_missing_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._write_package(root)
            (root / "valid_predictions.csv").write_text("tampered\n", encoding="utf-8")
            with self.assertRaisesRegex(SecurityError, "artifact hash mismatch"):
                self._audit(manifest_path)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._write_package(root)
            (root / "checkpoint.npz").unlink()
            with self.assertRaisesRegex(SecurityError, "artifact file is missing"):
                self._audit(manifest_path)

    def test_artifact_replacement_during_hash_is_rejected(self):
        for target in ("valid_predictions.csv", "resolved_config.json"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                manifest_path = self._write_package(root)
                changed = False

                def replace_after_hash(handle, path: Path, *, capture_bytes: bool):
                    nonlocal changed
                    result = _read_open_artifact(
                        handle, path, capture_bytes=capture_bytes
                    )
                    if path.name == target and not changed:
                        changed = True
                        path.write_bytes(b"replacement-after-first-hash\n")
                    return result

                with patch(
                    "tools.validate_contract._read_open_artifact",
                    side_effect=replace_after_hash,
                ):
                    with self.assertRaisesRegex(SecurityError, "changed"):
                        self._audit(manifest_path)
                self.assertTrue(changed)

    def test_replacement_after_semantic_snapshot_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._write_package(root)
            checks = 0

            def replace_after_initial_bindings(
                path, handle, path_signature, handle_signature,
            ):
                nonlocal checks
                _assert_artifact_binding(
                    path, handle, path_signature, handle_signature
                )
                checks += 1
                if checks == 5:
                    (root / "resolved_config.json").write_bytes(
                        b'{"model":"replacement"}\n'
                    )

            with patch(
                "tools.validate_contract._assert_artifact_binding",
                side_effect=replace_after_initial_bindings,
            ):
                with self.assertRaisesRegex(SecurityError, "changed"):
                    self._audit(manifest_path)
            self.assertGreaterEqual(checks, 5)

    def test_audit_manifest_rejects_resolved_config_semantic_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._write_package(root)
            drifted = deepcopy(self.config)
            drifted["model"]["embedding_dim"] = float(
                drifted["model"]["embedding_dim"]
            )
            write_json(root / "resolved_config.json", drifted)
            manifest = self._audit_input_with_current_hashes(root, manifest_path)
            write_json(manifest_path, manifest)
            with self.assertRaisesRegex(SecurityError, "content must equal"):
                self._audit(manifest_path)

    def test_audit_manifest_rejects_forged_experiment_identity_and_route(self):
        mutations = (
            ("experiment_id", "exp_forged", "experiment_id"),
            ("run_variant", "baseline", "run_variant"),
            ("config_path", "configs/approved/baseline_fm.json", "run_variant"),
            ("config_path", "../../outside.json", "approved candidate or baseline"),
            ("config_input_hash", "d" * 64, "config_input_hash"),
        )
        for field, value, message in mutations:
            with self.subTest(field=field, value=value), tempfile.TemporaryDirectory() as tmp:
                manifest_path = self._write_package(Path(tmp))
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest[field] = value
                write_json(manifest_path, manifest)
                with self.assertRaisesRegex(SecurityError, message):
                    self._audit(manifest_path)

    def test_audit_manifest_rejects_resolved_config_forgery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._write_package(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["config"]["resolved_run"]["seed"] = 7
            manifest["config_hash"] = stable_json_hash(manifest["config"])
            write_json(root / "resolved_config.json", manifest["config"])
            write_json(manifest_path, manifest)
            manifest = self._audit_input_with_current_hashes(root, manifest_path)
            write_json(manifest_path, manifest)
            with self.assertRaisesRegex(SecurityError, "approved repository config"):
                self._audit(manifest_path)

    def test_audit_manifest_rejects_forged_objective_seed_and_mode(self):
        cases = (
            ("objective", "pointwise_binary_cross_entropy", "objective"),
            ("seed", 7, "training.seed"),
            ("mode", "experiment", "valid-only"),
        )
        for field, value, message in cases:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                manifest_path = self._write_package(root)
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest[field] = value
                if field in {"seed", "mode"}:
                    manifest["config"]["resolved_run"][field] = value
                    manifest["config_hash"] = stable_json_hash(manifest["config"])
                    write_json(root / "resolved_config.json", manifest["config"])
                write_json(manifest_path, manifest)
                manifest = self._audit_input_with_current_hashes(root, manifest_path)
                write_json(manifest_path, manifest)
                with self.assertRaisesRegex(SecurityError, message):
                    self._audit(manifest_path)

    def test_audit_manifest_rejects_unrelated_approval_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = self._write_package(Path(tmp))
            with self.assertRaisesRegex(SecurityError, "not an ancestor"):
                self._audit(manifest_path, approved_ancestor=False)

    def test_baseline_config_approval_commit_must_be_an_ancestor(self):
        baseline_path = self.repo_root / "configs" / "approved" / "baseline_fm.json"
        raw_baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        record = deepcopy(self.manifest)
        record.update(
            run_variant="baseline",
            objective="pointwise_binary_cross_entropy",
            config_path="configs/approved/baseline_fm.json",
            config_input_hash=sha256_file(baseline_path),
        )
        record["config"] = {
            **raw_baseline,
            "resolved_run": {
                "experiment_id": "exp_001", "run_variant": "baseline",
                "seed": 0, "max_batches": None, "mode": "valid-only",
            },
        }
        record["config_hash"] = stable_json_hash(record["config"])
        with ExitStack() as stack, patch(
            "tools.audit_run._git_is_ancestor", side_effect=[True, False]
        ):
            with self.assertRaisesRegex(SecurityError, "baseline config.*not an ancestor"):
                verify_approved_repository_inputs(record, stack)

    def test_exp002_baseline_route_binds_the_approved_bpr_champion(self):
        spec_path = self.repo_root / "experiments" / "exp_002.json"
        baseline_path = self.repo_root / "configs" / "approved" / "exp_001.json"
        raw_baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        record = deepcopy(self.manifest)
        record.update(
            experiment_id="exp_002",
            experiment_spec_path="experiments/exp_002.json",
            experiment_spec_hash=sha256_file(spec_path),
            run_variant="baseline",
            objective="same_user_bpr",
            config_path="configs/approved/exp_001.json",
            config_input_hash=sha256_file(baseline_path),
        )
        record["config"] = {
            **raw_baseline,
            "resolved_run": {
                "experiment_id": "exp_002",
                "run_variant": "baseline",
                "seed": 0,
                "max_batches": None,
                "mode": "valid-only",
            },
        }
        record["config_hash"] = stable_json_hash(record["config"])
        validate_approved_run_route(record, self.repo_root)

        forged_objective = deepcopy(record)
        forged_objective["objective"] = "pointwise_binary_cross_entropy"
        with self.assertRaisesRegex(ValidationError, "manifest objective"):
            validate_approved_run_route(forged_objective, self.repo_root)

        candidate_on_baseline = deepcopy(record)
        candidate_on_baseline["config_path"] = "configs/candidates/bpr_fm.json"
        with self.assertRaisesRegex(ValidationError, "baseline config_path"):
            validate_approved_run_route(candidate_on_baseline, self.repo_root)

        baseline_on_candidate = deepcopy(record)
        baseline_on_candidate["run_variant"] = "candidate"
        with self.assertRaisesRegex(ValidationError, "candidate config_path"):
            validate_approved_run_route(baseline_on_candidate, self.repo_root)

    def test_candidate_semantics_reject_an_approved_baseline_config(self):
        spec = json.loads(self.spec_path.read_text(encoding="utf-8"))
        baseline_path = self.repo_root / "configs" / "approved" / "exp_001.json"
        raw_baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        record = deepcopy(self.manifest)
        with self.assertRaisesRegex(ValidationError, "candidate route"):
            validate_approved_run_semantics(record, spec, raw_baseline)

    def test_semantics_reject_spec_and_config_identity_forgery(self):
        spec = json.loads(self.spec_path.read_text(encoding="utf-8"))
        raw_candidate = json.loads(self.config_path.read_text(encoding="utf-8"))

        wrong_author = deepcopy(spec)
        wrong_author["author_role"] = "E"
        with self.assertRaisesRegex(ValidationError, "author_role"):
            validate_approved_run_semantics(
                self.manifest, wrong_author, raw_candidate
            )

        limited = deepcopy(raw_candidate)
        limited["training"]["max_batches"] = 2
        forged_limit = deepcopy(self.manifest)
        forged_limit["max_batches"] = 1
        with self.assertRaisesRegex(ValidationError, "max_batches"):
            validate_approved_run_semantics(forged_limit, spec, limited)

        unapproved_cli_limit = deepcopy(self.manifest)
        unapproved_cli_limit["max_batches"] = 1
        with self.assertRaisesRegex(ValidationError, "max_batches"):
            validate_approved_run_semantics(
                unapproved_cli_limit, spec, raw_candidate
            )

        baseline_path = self.repo_root / "configs" / "approved" / "baseline_fm.json"
        raw_baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        raw_baseline["experiment_id"] = "baseline_forged"
        baseline_manifest = deepcopy(self.manifest)
        baseline_manifest.update(
            run_variant="baseline",
            objective="pointwise_binary_cross_entropy",
        )
        with self.assertRaisesRegex(ValidationError, "baseline config experiment_id"):
            validate_approved_run_semantics(
                baseline_manifest, spec, raw_baseline
            )

    def _audit_input_with_current_hashes(
        self, root: Path, manifest_path: Path
    ) -> dict[str, object]:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for artifact in manifest["artifacts"]:
            artifact["sha256"] = sha256_file(root / artifact["path"])
        manifest["prediction_hash"] = next(
            artifact["sha256"]
            for artifact in manifest["artifacts"]
            if artifact["path"] == "valid_predictions.csv"
        )
        manifest["checkpoint_hash"] = next(
            artifact["sha256"]
            for artifact in manifest["artifacts"]
            if artifact["path"] == "checkpoint.npz"
        )
        return manifest

    def test_audit_manifest_rejects_top_level_cross_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._write_package(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["prediction_hash"] = "d" * 64
            write_json(manifest_path, manifest)
            with self.assertRaisesRegex(SecurityError, "prediction_hash must match"):
                self._audit(manifest_path)

    def test_audit_manifest_rejects_experiment_spec_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._write_package(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["experiment_spec_hash"] = "d" * 64
            write_json(manifest_path, manifest)
            with self.assertRaisesRegex(SecurityError, "experiment_spec_hash"):
                self._audit(manifest_path)

    def test_route_validator_rejects_unsafe_paths_status_and_config_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "experiments").mkdir()
            (root / "configs" / "candidates").mkdir(parents=True)
            (root / "configs" / "approved").mkdir(parents=True)
            candidate = root / "configs" / "candidates" / "candidate.json"
            baseline = root / "configs" / "approved" / "baseline.json"
            candidate.write_text(
                '{"objective":{"name":"same_user_bpr"},'
                '"training":{"seed":0,"max_batches":null}}\n',
                encoding="utf-8",
            )
            baseline.write_text(
                '{"experiment_id":"baseline_fm",'
                '"objective":{"name":"pointwise_binary_cross_entropy"},'
                '"training":{"seed":0,"max_batches":null}}\n',
                encoding="utf-8",
            )
            spec = json.loads(self.spec_path.read_text(encoding="utf-8"))
            spec["experiment_id"] = "exp_route"
            spec["implementation_config"] = "configs/candidates/candidate.json"
            spec["baseline"]["approved_config"] = "configs/approved/baseline.json"
            spec_path = root / "experiments" / "exp_route.json"
            write_json(spec_path, spec)
            raw_config = json.loads(candidate.read_text(encoding="utf-8"))
            manifest = deepcopy(self.manifest)
            manifest.update(
                experiment_id="exp_route",
                experiment_spec_path="experiments/exp_route.json",
                experiment_spec_hash=sha256_file(spec_path),
                config_path="configs/candidates/candidate.json",
                config_input_hash=sha256_file(candidate),
            )
            manifest["config"] = {
                **raw_config,
                "resolved_run": {
                    "experiment_id": "exp_route", "run_variant": "candidate",
                    "seed": 0, "max_batches": None, "mode": "valid-only",
                },
            }
            manifest["config_hash"] = stable_json_hash(manifest["config"])
            validate_approved_run_route(manifest, root)

            spec_link = root / "experiments" / "spec-link.json"
            try:
                spec_link.symlink_to(spec_path.name)
            except OSError as error:
                self.skipTest(f"symlink creation is unavailable: {error}")
            forged_spec_link = deepcopy(manifest)
            forged_spec_link["experiment_spec_path"] = "experiments/spec-link.json"
            with self.assertRaisesRegex(ValidationError, "symlink"):
                validate_approved_run_route(forged_spec_link, root)

            config_link = root / "configs" / "candidates" / "config-link.json"
            config_link.symlink_to(candidate.name)
            linked_spec = deepcopy(spec)
            linked_spec["implementation_config"] = "configs/candidates/config-link.json"
            write_json(spec_path, linked_spec)
            forged_config_link = deepcopy(manifest)
            forged_config_link["experiment_spec_hash"] = sha256_file(spec_path)
            forged_config_link["config_path"] = "configs/candidates/config-link.json"
            with self.assertRaisesRegex(ValidationError, "symlink"):
                validate_approved_run_route(forged_config_link, root)
            write_json(spec_path, spec)
            manifest["experiment_spec_hash"] = sha256_file(spec_path)

            for field, value in (
                ("experiment_spec_path", "../experiments/exp_route.json"),
                ("experiment_spec_path", "/absolute/spec.json"),
                ("experiment_spec_path", "C:\\spec.json"),
                ("experiment_spec_path", "experiments\\exp_route.json"),
                ("config_path", "../configs/candidates/candidate.json"),
                ("config_path", "/absolute/config.json"),
                ("config_path", "C:\\config.json"),
                ("config_path", "configs\\candidates\\candidate.json"),
            ):
                forged = deepcopy(manifest)
                forged[field] = value
                with self.subTest(field=field, value=value), self.assertRaisesRegex(
                    ValidationError, "normalized|does not match approved spec route"
                ):
                    validate_approved_run_route(forged, root)

            unapproved = deepcopy(spec)
            unapproved["status"] = "PROPOSED"
            write_json(spec_path, unapproved)
            manifest["experiment_spec_hash"] = sha256_file(spec_path)
            with self.assertRaisesRegex(ValidationError, "APPROVED_FOR_IMPLEMENTATION"):
                validate_approved_run_route(manifest, root)

            write_json(spec_path, spec)
            manifest["experiment_spec_hash"] = sha256_file(spec_path)
            manifest["config"]["resolved_run"]["mode"] = "experiment"
            manifest["config_hash"] = stable_json_hash(manifest["config"])
            with self.assertRaisesRegex(ValidationError, "cannot be rebuilt"):
                validate_approved_run_route(manifest, root)

    def test_audit_manifest_rejects_duplicate_and_traversal_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._write_package(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["artifacts"].append(deepcopy(manifest["artifacts"][0]))
            write_json(manifest_path, manifest)
            with self.assertRaisesRegex(SecurityError, "duplicate artifact path"):
                self._audit(manifest_path)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._write_package(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["artifacts"][0]["path"] = "../valid_predictions.csv"
            write_json(manifest_path, manifest)
            with self.assertRaisesRegex(SecurityError, "normalized relative path"):
                self._audit(manifest_path)

    def test_audit_manifest_rejects_artifact_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._write_package(root)
            target = root.parent / f"{root.name}-outside-predictions.csv"
            target.write_bytes((root / "valid_predictions.csv").read_bytes())
            (root / "valid_predictions.csv").unlink()
            try:
                (root / "valid_predictions.csv").symlink_to(target)
            except OSError as error:
                self.skipTest(f"symlink creation is unavailable: {error}")
            try:
                with self.assertRaisesRegex(SecurityError, "not a symlink"):
                    self._audit(manifest_path)
            finally:
                target.unlink(missing_ok=True)


class FinalApprovalTests(unittest.TestCase):
    def setUp(self):
        self.commit = "a" * 40
        self.hashes = {"starter/evaluate.py": "b" * 64}
        self.approval = {
            "schema_version": 1,
            "contract_type": "final_approval",
            "experiment_id": "exp_001",
            "commit_sha": self.commit,
            "approved": True,
            "approved_by": "Human Reviewer",
            "approved_at": "2026-08-29T15:00:00+08:00",
            "protected_hashes": self.hashes,
        }

    def test_accepts_human_approval_for_clean_commit_sha(self):
        validate_approval_record(self.approval, self.commit, False, self.hashes)

    def test_rejects_non_human_or_missing_approval(self):
        self.approval["approved_by"] = "Codex"
        with self.assertRaises(SecurityError):
            validate_approval_record(self.approval, self.commit, False, self.hashes)
        self.approval["approved_by"] = "Human Reviewer"
        self.approval["approved"] = False
        with self.assertRaises(SecurityError):
            validate_approval_record(self.approval, self.commit, False, self.hashes)

    def test_rejects_placeholder_approver_dirty_tree_and_wrong_commit(self):
        self.approval["approved_by"] = "REPLACE_WITH_HUMAN_NAME"
        with self.assertRaises(SecurityError):
            validate_approval_record(self.approval, self.commit, False, self.hashes)
        self.approval["approved_by"] = "Human Reviewer"
        with self.assertRaises(SecurityError):
            validate_approval_record(self.approval, self.commit, True, self.hashes)
        self.approval["commit_sha"] = "d" * 40
        with self.assertRaises(SecurityError):
            validate_approval_record(self.approval, self.commit, False, self.hashes)

    def test_rejects_legacy_alias_in_final_approval(self):
        self.approval["frozen_commit"] = self.commit
        with self.assertRaisesRegex(SecurityError, "forbidden legacy field"):
            validate_approval_record(self.approval, self.commit, False, self.hashes)


if __name__ == "__main__":
    unittest.main()
