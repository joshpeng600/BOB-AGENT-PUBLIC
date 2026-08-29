"""Shared hashing and Git-state checks for the evaluation gate."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTECTED_MANIFEST = REPO_ROOT / "protected_manifest.json"


class SecurityError(RuntimeError):
    """Raised when protected project state cannot be trusted."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise SecurityError(f"Missing required file: {path}") from error
    except json.JSONDecodeError as error:
        raise SecurityError(f"Invalid JSON in {path}: {error}") from error
    if not isinstance(value, dict):
        raise SecurityError(f"Expected a JSON object in {path}")
    return value


def expected_protected_hashes() -> dict[str, str]:
    manifest = load_json(PROTECTED_MANIFEST)
    if manifest.get("algorithm") != "sha256":
        raise SecurityError("Protected manifest must use sha256")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise SecurityError("Protected manifest has no files")
    return {str(path): str(digest) for path, digest in files.items()}


def verify_protected_files() -> dict[str, str]:
    expected = expected_protected_hashes()
    actual: dict[str, str] = {}
    for relative_path, expected_digest in expected.items():
        path = REPO_ROOT / relative_path
        if not path.is_file():
            raise SecurityError(f"Protected file is missing: {relative_path}")
        digest = sha256_file(path)
        actual[relative_path] = digest
        if digest != expected_digest:
            raise SecurityError(
                f"Protected hash mismatch for {relative_path}: "
                f"expected {expected_digest}, got {digest}"
            )
    return actual


def git_head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def git_is_dirty() -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())
