from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.common import sha256_file, stable_json_hash, write_json
from tools.audit_run import audit_manifest, is_test_scoring_command, validate_manifest_record
from tools.final_approval import validate_approval_record
from tools.project_security import SecurityError


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.commit = "a" * 40
        self.hashes = {"starter/evaluate.py": "b" * 64}
        self.digest = "c" * 64
        self.config = {"model": "fm"}
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
            "config_path": "configs/candidates/bpr_fm.json",
            "config_hash": stable_json_hash(self.config),
            "config": self.config,
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
        for field in ("config_hash", "data_hash", "prediction_hash", "checkpoint_hash"):
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

    def _audit(self, manifest_path: Path) -> dict[str, object]:
        with (
            patch("tools.audit_run.verify_protected_files", return_value=self.hashes),
            patch("tools.audit_run.expected_protected_hashes", return_value=self.hashes),
            patch("tools.audit_run.git_head", return_value=self.commit),
            patch("tools.audit_run.git_is_dirty", return_value=False),
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

    def test_audit_manifest_rejects_resolved_config_semantic_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.config = {"value": 1}
            self.manifest["config"] = self.config
            self.manifest["config_hash"] = stable_json_hash(self.config)
            manifest_path = self._write_package(root)
            write_json(root / "resolved_config.json", {"value": 1.0})
            manifest = self._audit_input_with_current_hashes(root, manifest_path)
            write_json(manifest_path, manifest)
            with self.assertRaisesRegex(SecurityError, "content must equal"):
                self._audit(manifest_path)

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
