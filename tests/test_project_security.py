import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import project_security
from tools.project_security import REPO_ROOT, sha256_file, verify_protected_files


class ProjectSecurityTests(unittest.TestCase):
    def test_normalized_hash_accepts_lf_and_crlf_with_identical_content(self):
        with tempfile.TemporaryDirectory() as tempdir:
            lf_path = Path(tempdir) / "lf.py"
            crlf_path = Path(tempdir) / "crlf.py"
            lf_path.write_bytes(b"first line\nsecond line\n")
            crlf_path.write_bytes(b"first line\r\nsecond line\r\n")

            expected = hashlib.sha256(lf_path.read_bytes()).hexdigest()
            self.assertEqual(
                sha256_file(lf_path, normalize_line_endings=True), expected
            )
            self.assertEqual(
                sha256_file(crlf_path, normalize_line_endings=True), expected
            )
            self.assertNotEqual(sha256_file(lf_path), sha256_file(crlf_path))

    def test_content_change_still_fails_normalized_hash_equivalence(self):
        with tempfile.TemporaryDirectory() as tempdir:
            original = Path(tempdir) / "original.py"
            changed = Path(tempdir) / "changed.py"
            original.write_bytes(b"score = 1\n")
            changed.write_bytes(b"score = 2\r\n")
            self.assertNotEqual(
                sha256_file(original, normalize_line_endings=True),
                sha256_file(changed, normalize_line_endings=True),
            )

    def test_full_verifier_accepts_simulated_windows_crlf_checkout(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            protected = root / "starter" / "evaluate.py"
            protected.parent.mkdir()
            lf_bytes = b"def evaluate():\n    return 1\n"
            protected.write_bytes(lf_bytes.replace(b"\n", b"\r\n"))
            manifest = root / "protected_manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "algorithm": "sha256",
                        "files": {
                            "starter/evaluate.py": hashlib.sha256(lf_bytes).hexdigest()
                        },
                    }
                ),
                encoding="utf-8",
            )
            with (
                patch.object(project_security, "REPO_ROOT", root),
                patch.object(project_security, "PROTECTED_MANIFEST", manifest),
            ):
                hashes = project_security.verify_protected_files()
            self.assertEqual(
                hashes["starter/evaluate.py"], hashlib.sha256(lf_bytes).hexdigest()
            )

    def test_protected_files_are_declared_lf_in_gitattributes(self):
        paths = [
            "starter/evaluate.py",
            "starter/data.py",
            "starter/submit.py",
            "starter/baseline_scores.json",
            "protected_manifest.json",
        ]
        result = subprocess.run(
            ["git", "check-attr", "eol", "--", *paths],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        for path in paths:
            self.assertIn(f"{path}: eol: lf", result.stdout)

    def test_current_protected_files_match_manifest(self):
        hashes = verify_protected_files()
        self.assertIn("starter/evaluate.py", hashes)


if __name__ == "__main__":
    unittest.main()
