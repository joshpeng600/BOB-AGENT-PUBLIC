"""Independently audit a run manifest before accepting its evidence."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from tools.project_security import (
    SecurityError,
    expected_protected_hashes,
    git_head,
    git_is_dirty,
    load_json,
    verify_protected_files,
)


FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


def is_test_scoring_command(command: str) -> bool:
    normalized = " ".join(command.casefold().split())
    selects_test = "--split test" in normalized or "--split=test" in normalized
    scores = (
        "--score" in normalized
        or "safe_evaluate" in normalized
        or "evaluate.py" in normalized
    )
    return selects_test and scores


def validate_manifest_record(
    record: dict[str, Any],
    current_commit: str,
    actual_dirty: bool,
    protected_hashes: dict[str, str],
) -> None:
    experiment_id = record.get("experiment_id")
    if not isinstance(experiment_id, str) or not experiment_id.strip():
        raise SecurityError("experiment_id is required")
    commit_sha = record.get("commit_sha")
    if not isinstance(commit_sha, str) or not FULL_SHA.fullmatch(commit_sha):
        raise SecurityError("commit_sha must be a complete 40-character SHA")
    if commit_sha != current_commit:
        raise SecurityError("manifest commit_sha does not match the current Git commit")
    if record.get("worktree_clean") is not True:
        raise SecurityError("manifest must explicitly record worktree_clean=true")
    if actual_dirty:
        raise SecurityError("actual worktree is dirty")

    config = record.get("config")
    if not isinstance(config, dict) or not config:
        raise SecurityError("config must be a non-empty object")
    data = record.get("data")
    if not isinstance(data, dict) or not data:
        raise SecurityError("data must be a non-empty object")
    if not str(data.get("hash", "")).strip():
        raise SecurityError("data.hash is required")
    seed = record.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise SecurityError("seed must be an integer")
    try:
        dev_max_date = int(record.get("dev_max_date"))
    except (TypeError, ValueError) as error:
        raise SecurityError("dev_max_date is required") from error
    if dev_max_date > 20220428:
        raise SecurityError("dev_max_date exceeds 20220428; possible test leakage")

    if record.get("protected_hashes") != protected_hashes:
        raise SecurityError("protected_hashes do not match protected_manifest.json")
    commands = record.get("commands")
    if not isinstance(commands, list) or not all(isinstance(item, str) for item in commands):
        raise SecurityError("commands must be a list of strings")
    forbidden = [command for command in commands if is_test_scoring_command(command)]
    if forbidden:
        raise SecurityError(f"test scoring command found: {forbidden[0]}")


def audit_manifest(manifest_path: Path) -> dict[str, Any]:
    actual_hashes = verify_protected_files()
    expected_hashes = expected_protected_hashes()
    if actual_hashes != expected_hashes:
        raise SecurityError("Protected files do not match their manifest")
    record = load_json(manifest_path)
    validate_manifest_record(record, git_head(), git_is_dirty(), expected_hashes)
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()
    try:
        audit_manifest(args.manifest)
    except SecurityError as error:
        print(f"AUDIT FAILED: {error}")
        return 1
    print("AUDIT PASSED: commit, clean state, data boundary, hashes, and commands verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
