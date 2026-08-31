from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from tools.final_submission import (
    freeze_final_submission,
    load_hidden_identities,
    validate_submission_candidate,
)
from tools.project_security import SecurityError


class FinalSubmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.identities = self.root / "identities.csv"
        self.candidate = self.root / "candidate.csv"
        with self.identities.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["row_id", "user_id", "video_id"])
            writer.writerows([[0, "u1", "v1"], [1, "u1", "v2"]])
        with self.candidate.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["row_id", "user_id", "video_id", "score"])
            writer.writerows([[0, "u1", "v1", 0.9], [1, "u1", "v2", 0.1]])

    def tearDown(self):
        self.temp.cleanup()

    def test_freezes_label_free_submission_without_metrics(self):
        output = self.root / "final" / "submission.csv"
        manifest_path = self.root / "final" / "manifest.json"
        manifest = freeze_final_submission(
            candidate=self.candidate,
            identities_path=self.identities,
            output=output,
            manifest_path=manifest_path,
            approval={"experiment_id": "exp_003"},
        )
        self.assertEqual(output.read_bytes(), self.candidate.read_bytes())
        self.assertEqual(manifest["rows"], 2)
        self.assertFalse(manifest["hidden_test_labels_read"])
        self.assertFalse(manifest["local_test_metrics_produced"])
        self.assertTrue(manifest["organizer_side_scoring_required"])
        self.assertNotIn("GAUC", json.dumps(manifest))
        with self.assertRaisesRegex(SecurityError, "already exists"):
            freeze_final_submission(
                candidate=self.candidate,
                identities_path=self.identities,
                output=output,
                manifest_path=manifest_path,
                approval={"experiment_id": "exp_003"},
            )

    def test_rejects_identity_label_columns(self):
        self.identities.write_text(
            "row_id,user_id,video_id,label\n0,u1,v1,1\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(SecurityError, "label columns are forbidden"):
            load_hidden_identities(self.identities)

    def test_rejects_identity_mismatch_and_nonfinite_scores(self):
        identities = load_hidden_identities(self.identities)
        self.candidate.write_text(
            "row_id,user_id,video_id,score\n0,u1,wrong,0.9\n1,u1,v2,0.1\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(SecurityError, "identity mismatch"):
            validate_submission_candidate(self.candidate, identities)
        self.candidate.write_text(
            "row_id,user_id,video_id,score\n0,u1,v1,nan\n1,u1,v2,0.1\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(SecurityError, "NaN/Inf"):
            validate_submission_candidate(self.candidate, identities)


if __name__ == "__main__":
    unittest.main()
