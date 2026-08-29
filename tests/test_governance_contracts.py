import json
from pathlib import Path
import subprocess
import unittest

from scripts.check_repository_contracts import (
    contract_field_violations,
    experiment_violations,
    provenance_violations,
)


ROOT = Path(__file__).resolve().parents[1]


class GovernanceContractTests(unittest.TestCase):
    def test_policy_thresholds_are_fixed(self):
        policy = json.loads((ROOT / "governance" / "policy.json").read_text(encoding="utf-8"))
        self.assertEqual(policy["epsilon"], 0.002)
        self.assertEqual(policy["consecutive_no_improve"], 3)
        self.assertEqual(policy["automatic_repair"]["max_attempts"], 1)
        self.assertFalse(policy["test_evaluation"]["ordinary_experiments_allowed"])

    def test_ordinary_experiment_rejects_test_scoring(self):
        document = {"evaluation_split": "test", "test_metrics": ["GAUC"]}
        self.assertEqual(len(experiment_violations(document)), 2)

    def test_validation_experiment_is_allowed(self):
        document = {"evaluation_split": "validation", "metrics": ["GAUC", "nDCG@5"]}
        self.assertEqual(experiment_violations(document), [])

    def test_artifact_requires_full_commit_sha(self):
        bad = {"contract_type": "run_manifest", "commit_sha": "abc123", "artifacts": []}
        placeholder = {"contract_type": "metrics", "commit_sha": "0" * 40}
        good = {"contract_type": "run_manifest", "commit_sha": "a" * 40, "artifacts": []}
        self.assertTrue(provenance_violations(bad, Path("run_manifest.json")))
        self.assertTrue(provenance_violations(placeholder, Path("metrics.json")))
        self.assertEqual(provenance_violations(good, Path("run_manifest.json")), [])

    def test_canonical_contract_fields_are_enforced(self):
        old = {"contract_type": "metrics", "exp_id": "x", "base_commit": "a" * 40}
        current = {
            "contract_type": "metrics",
            "experiment_id": "x",
            "commit_sha": "a" * 40,
        }
        self.assertTrue(contract_field_violations(old))
        self.assertEqual(contract_field_violations(current), [])

    def test_all_protected_text_is_checked_out_with_lf(self):
        paths = [
            entry["path"]
            for entry in json.loads(
                (ROOT / "governance" / "protected_files.json").read_text(encoding="utf-8")
            )["files"]
        ] + ["governance/protected_files.json", "protected_manifest.json"]
        result = subprocess.run(
            ["git", "check-attr", "eol", "--", *paths],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        for path in paths:
            self.assertIn(f"{path}: eol: lf", result.stdout)


if __name__ == "__main__":
    unittest.main()
