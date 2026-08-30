import unittest

from tools.common import stable_json_hash
from tools.audit_run import is_test_scoring_command, validate_manifest_record
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
