"""Deny test operations unless a clean frozen commit has human approval."""

from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from tools.common import ValidationError
from tools.project_security import (
    SecurityError,
    expected_protected_hashes,
    git_head,
    git_is_dirty,
    load_json,
    verify_protected_files,
)
from tools.validate_contract import validate_contract


FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
NON_HUMAN_APPROVERS = {
    "", "todo", "tbd", "placeholder", "replace_with_human_name",
    "codex", "agent", "ai",
}


def validate_approval_record(
    record: dict[str, Any],
    current_commit: str,
    actual_dirty: bool,
    protected_hashes: dict[str, str],
) -> None:
    try:
        validate_contract("final_approval", record)
    except ValidationError as error:
        raise SecurityError(f"invalid final_approval contract: {error}") from error

    experiment_id = record.get("experiment_id")
    if not isinstance(experiment_id, str) or not experiment_id.strip():
        raise SecurityError("experiment_id is required")
    commit_sha = record.get("commit_sha")
    if not isinstance(commit_sha, str) or not FULL_SHA.fullmatch(commit_sha):
        raise SecurityError("commit_sha must be a complete 40-character SHA")
    if commit_sha != current_commit:
        raise SecurityError("commit_sha does not match the current Git commit")
    if actual_dirty:
        raise SecurityError("Worktree is dirty; test operation denied")
    if record.get("approved") is not True:
        raise SecurityError("Human approval is missing")

    approver = str(record.get("approved_by", "")).strip()
    if approver.casefold() in NON_HUMAN_APPROVERS:
        raise SecurityError("approved_by must identify a human approver")

    approved_at = record.get("approved_at")
    if not isinstance(approved_at, str):
        raise SecurityError("approved_at must be an ISO-8601 timestamp")
    try:
        datetime.fromisoformat(approved_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise SecurityError("approved_at must be an ISO-8601 timestamp") from error

    if record.get("protected_hashes") != protected_hashes:
        raise SecurityError("Approval protected_hashes do not match the manifest")


def verify_final_approval(approval_path: Path) -> dict[str, Any]:
    actual_hashes = verify_protected_files()
    expected_hashes = expected_protected_hashes()
    if actual_hashes != expected_hashes:
        raise SecurityError("Protected files do not match their manifest")
    record = load_json(approval_path)
    validate_approval_record(record, git_head(), git_is_dirty(), expected_hashes)
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approval", required=True, type=Path)
    args = parser.parse_args()
    try:
        verify_final_approval(args.approval)
    except SecurityError as error:
        print(f"DENIED: {error}")
        return 1
    print("APPROVED: commit_sha, clean worktree, protected hashes, and human approval verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
