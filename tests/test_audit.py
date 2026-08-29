import unittest

from tools.audit_run import is_test_scoring_command, validate_manifest_record
from tools.final_approval import validate_approval_record
from tools.project_security import SecurityError


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.commit = "a" * 40
        self.hashes = {"starter/evaluate.py": "b" * 64}
        self.manifest = {
            "experiment_id": "exp001",
            "run_id": "exp001",
            "commit_sha": self.commit,
            "worktree_clean": True,
            "config": {"model": "fm"},
            "data": {"dataset": "KuaiRand-Pure", "split": "valid", "hash": "c" * 64},
            "seed": 0,
            "dev_max_date": 20220428,
            "protected_hashes": self.hashes,
            "commands": ["python3 train.py --split valid"],
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
            "experiment_id": "exp001",
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


if __name__ == "__main__":
    unittest.main()
