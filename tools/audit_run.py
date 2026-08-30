"""Independently audit a run manifest before accepting its evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, BinaryIO

from tools.common import ValidationError, sha256_file, stable_json_hash
from tools.project_security import (
    SecurityError,
    expected_protected_hashes,
    git_head,
    git_is_dirty,
    load_json,
    verify_protected_files,
)
from tools.validate_contract import validate_artifact_files, validate_contract


FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
REPO_ROOT = Path(__file__).resolve().parents[1]


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
    try:
        validate_contract("run_manifest", record)
    except ValidationError as error:
        raise SecurityError(f"invalid run_manifest contract: {error}") from error

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
    if record.get("config_hash") != stable_json_hash(config):
        raise SecurityError("config_hash does not match the recorded config")
    data = record.get("data")
    if not isinstance(data, dict) or not data:
        raise SecurityError("data must be a non-empty object")
    if data.get("hash") != record.get("data_hash"):
        raise SecurityError("data.hash must match data_hash")
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


@dataclass(frozen=True)
class RepositoryInput:
    path: Path
    handle: BinaryIO
    path_signature: tuple[int, int, int, int, int, int]
    handle_signature: tuple[int, int, int, int, int, int]
    document: dict[str, Any]
    digest: str


def _signature(metadata: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        int(metadata.st_dev), int(metadata.st_ino), int(metadata.st_mode),
        int(metadata.st_size), int(metadata.st_mtime_ns), int(metadata.st_ctime_ns),
    )


def _identity(metadata: os.stat_result) -> tuple[int, int, int]:
    return (int(metadata.st_dev), int(metadata.st_ino), int(metadata.st_mode))


def _repository_path(raw_path: Any, directory: str, label: str) -> Path:
    if not isinstance(raw_path, str) or not raw_path:
        raise SecurityError(f"{label} must be a repository-relative path")
    path = Path(raw_path)
    posix_path = PurePosixPath(raw_path)
    windows_path = PureWindowsPath(raw_path)
    if (
        path.is_absolute()
        or posix_path.is_absolute()
        or windows_path.is_absolute()
        or bool(windows_path.drive)
        or "\\" in raw_path
        or ".." in posix_path.parts
        or posix_path.as_posix() != raw_path
    ):
        raise SecurityError(f"{label} must be a normalized relative path")
    if not posix_path.parts or posix_path.parts[0] != directory:
        raise SecurityError(f"{label} must be under {directory}/")
    candidate = REPO_ROOT / path
    try:
        candidate.resolve().relative_to(REPO_ROOT.resolve())
    except ValueError as error:
        raise SecurityError(f"{label} escapes the repository") from error
    return candidate


def _read_open(handle: BinaryIO) -> tuple[bytes, str]:
    before = _signature(os.fstat(handle.fileno()))
    handle.seek(0)
    raw = handle.read()
    after = _signature(os.fstat(handle.fileno()))
    if before != after:
        raise SecurityError("repository input changed while reading")
    return raw, hashlib.sha256(raw).hexdigest()


def _open_repository_json(
    stack: ExitStack, raw_path: Any, directory: str, label: str,
) -> RepositoryInput:
    candidate = _repository_path(raw_path, directory, label)
    try:
        initial = os.lstat(candidate)
    except OSError as error:
        raise SecurityError(f"{label} is missing: {error}") from error
    if stat.S_ISLNK(initial.st_mode) or not stat.S_ISREG(initial.st_mode):
        raise SecurityError(f"{label} must be an ordinary file, not a symlink")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(candidate, flags)
    except OSError as error:
        raise SecurityError(f"cannot safely open {label}: {error}") from error
    try:
        handle = stack.enter_context(os.fdopen(descriptor, "rb"))
    except BaseException:
        os.close(descriptor)
        raise
    opened = os.fstat(handle.fileno())
    bound = os.lstat(candidate)
    if (
        not stat.S_ISREG(opened.st_mode)
        or _identity(initial) != _identity(opened)
        or _identity(bound) != _identity(opened)
    ):
        raise SecurityError(f"{label} path changed while opening")
    raw, digest = _read_open(handle)
    second_raw, second_digest = _read_open(handle)
    if raw != second_raw or digest != second_digest:
        raise SecurityError(f"{label} bytes changed while reading")
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SecurityError(f"{label} is invalid JSON: {error}") from error
    if not isinstance(document, dict):
        raise SecurityError(f"{label} root must be an object")
    return RepositoryInput(
        candidate, handle, _signature(bound), _signature(opened), document, digest
    )


def _assert_repository_input(binding: RepositoryInput, label: str) -> None:
    try:
        current_path = os.lstat(binding.path)
        current_handle = os.fstat(binding.handle.fileno())
    except OSError as error:
        raise SecurityError(f"{label} binding changed: {error}") from error
    if (
        _signature(current_path) != binding.path_signature
        or _signature(current_handle) != binding.handle_signature
    ):
        raise SecurityError(f"{label} path changed during audit")
    _, digest = _read_open(binding.handle)
    if digest != binding.digest:
        raise SecurityError(f"{label} bytes changed during audit")


def verify_approved_repository_inputs(
    record: dict[str, Any], stack: ExitStack,
) -> tuple[RepositoryInput, RepositoryInput]:
    spec_binding = _open_repository_json(
        stack, record.get("experiment_spec_path"), "experiments", "experiment_spec_path"
    )
    if spec_binding.digest != record.get("experiment_spec_hash"):
        raise SecurityError("experiment_spec_hash does not match the recorded experiment spec")
    try:
        validate_contract("experiment_spec", spec_binding.document)
    except ValidationError as error:
        raise SecurityError(f"invalid approved experiment spec: {error}") from error
    spec = spec_binding.document
    if spec.get("status") != "APPROVED_FOR_IMPLEMENTATION":
        raise SecurityError("experiment spec is not APPROVED_FOR_IMPLEMENTATION")
    if spec.get("experiment_id") != record.get("experiment_id"):
        raise SecurityError("manifest experiment_id does not match the approved experiment spec")

    candidate_path = str(spec.get("implementation_config", ""))
    baseline = spec.get("baseline")
    if not isinstance(baseline, dict):
        raise SecurityError("experiment spec baseline must be an object")
    baseline_path = str(baseline.get("approved_config", ""))
    _repository_path(candidate_path, "configs", "implementation_config")
    _repository_path(baseline_path, "configs", "baseline.approved_config")
    config_path = record.get("config_path")
    if config_path == candidate_path:
        expected_variant = "candidate"
    elif config_path == baseline_path:
        expected_variant = "baseline"
    else:
        raise SecurityError("config_path is not an approved candidate or baseline route")
    if record.get("run_variant") != expected_variant:
        raise SecurityError("run_variant does not match the approved config route")

    config_binding = _open_repository_json(
        stack, config_path, "configs", "config_path"
    )
    if config_binding.digest != record.get("config_input_hash"):
        raise SecurityError("config_input_hash does not match the raw repository config bytes")
    raw_config = config_binding.document
    resolved_run = record.get("config", {}).get("resolved_run")
    if not isinstance(resolved_run, dict):
        raise SecurityError("manifest config.resolved_run is required")
    expected_runtime = {
        "experiment_id": spec["experiment_id"],
        "run_variant": expected_variant,
        "seed": record.get("seed"),
        "max_batches": record.get("max_batches"),
        "mode": record.get("mode"),
    }
    expected_config = {**raw_config, "resolved_run": expected_runtime}
    if resolved_run != expected_runtime or record.get("config") != expected_config:
        raise SecurityError("manifest config does not match the approved repository config and runtime")
    if record.get("config_hash") != stable_json_hash(expected_config):
        raise SecurityError("config_hash does not match the approved resolved config")
    return spec_binding, config_binding


def audit_manifest(manifest_path: Path) -> dict[str, Any]:
    actual_hashes = verify_protected_files()
    expected_hashes = expected_protected_hashes()
    if actual_hashes != expected_hashes:
        raise SecurityError("Protected files do not match their manifest")
    record = load_json(manifest_path)
    validate_manifest_record(record, git_head(), git_is_dirty(), expected_hashes)
    with ExitStack() as stack:
        spec_binding, config_binding = verify_approved_repository_inputs(record, stack)
        try:
            validate_artifact_files(record, manifest_path.resolve().parent)
        except ValidationError as error:
            raise SecurityError(f"artifact audit failed: {error}") from error
        _assert_repository_input(spec_binding, "experiment spec")
        _assert_repository_input(config_binding, "config")
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
