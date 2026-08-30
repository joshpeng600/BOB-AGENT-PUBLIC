from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
import sys
from contextlib import ExitStack
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, BinaryIO

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.common import (
    VALID_END,
    ValidationError,
    read_json,
    stable_json_hash,
)


FULL_SHA = re.compile(r"[0-9a-f]{40}")
SHA256 = re.compile(r"[0-9a-f]{64}")
EXPERIMENT_ID = re.compile(r"exp[-_][A-Za-z0-9][A-Za-z0-9_-]*")
FORBIDDEN_ALIASES = {"exp_id", "base_commit", "commit", "frozen_commit"}
REQUIRED_COMPLETED_ARTIFACTS = {
    "valid_predictions.csv",
    "checkpoint.npz",
    "resolved_config.json",
    "training_history.json",
    "runner_metrics.json",
}
SUPPORTED_OBJECTIVES = {"pointwise_binary_cross_entropy", "same_user_bpr"}

REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "experiment_spec": (
        "schema_version", "contract_type", "experiment_id", "author_role",
        "created_at_utc", "approved_against_commit_sha", "status", "change_type",
        "hypothesis", "scope", "task", "baseline", "implementation_config",
        "role_deliverables", "run_command", "max_runtime_seconds",
        "automatic_repair_attempts",
    ),
    "feature_proposal": (
        "schema_version", "contract_type", "experiment_id", "proposal_id",
        "author_role", "created_at_utc", "approved_against_commit_sha",
        "implementation_commit_sha", "name", "hypothesis", "inputs", "transform",
        "leakage_review", "ablation_plan", "status",
    ),
    "model_proposal": (
        "schema_version", "contract_type", "experiment_id", "proposal_id",
        "author_role", "created_at_utc", "approved_against_commit_sha",
        "implementation_commit_sha", "name", "hypothesis", "model_family",
        "objective", "sampling", "input_output", "hyperparameters",
        "dependency_changes", "resource_estimate", "failure_conditions", "fallback",
        "validation_claim", "status",
    ),
    "run_manifest": (
        "schema_version", "contract_type", "experiment_id", "run_id", "commit_sha",
        "worktree_clean", "started_at_utc", "finished_at_utc", "executor_role",
        "experiment_spec_path", "experiment_spec_hash", "run_variant", "config_path",
        "config_input_hash", "config_hash", "config", "data", "data_hash", "seed",
        "dev_max_date", "environment",
        "protected_hashes", "commands", "prediction_hash", "checkpoint_hash",
        "artifacts", "status",
    ),
    "metrics": (
        "schema_version", "contract_type", "experiment_id", "run_id",
        "baseline_experiment_id", "commit_sha", "worktree_clean", "evaluator_role",
        "status", "hypothesis", "code_diff", "split", "metrics", "errors",
        "recovery", "manual_interventions", "tokens", "wall_time_seconds",
        "iterations", "gpu_hours", "config", "data", "seed", "protected_hashes",
        "artifact_manifest_path",
    ),
    "decision_request": (
        "schema_version", "contract_type", "experiment_id", "request_id",
        "requested_at_utc", "requested_by_role", "approved_against_commit_sha",
        "trigger", "summary", "evidence_paths", "options", "automation_paused",
        "status",
    ),
    "final_approval": (
        "schema_version", "contract_type", "experiment_id", "commit_sha", "approved",
        "approved_by", "approved_at", "protected_hashes",
    ),
}

ALIASES = {
    "experiment-spec": "experiment_spec",
    "feature-proposal": "feature_proposal",
    "model-proposal": "model_proposal",
    "run-manifest": "run_manifest",
    "decision-request": "decision_request",
    "final-approval": "final_approval",
}


def _canonical_type(contract_type: str) -> str:
    return ALIASES.get(contract_type, contract_type.replace("-", "_"))


def _require_object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{path} must be an object")
    return value


def _require_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValidationError(f"{path} must be an array")
    return value


def _validate_sha(value: Any, path: str, *, optional: bool = False) -> None:
    if value is None and optional:
        return
    if not isinstance(value, str) or not FULL_SHA.fullmatch(value) or value == "0" * 40:
        raise ValidationError(f"{path} must be a non-zero lowercase 40-character SHA")


def _validate_sha256(value: Any, path: str) -> None:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise ValidationError(f"{path} must be a lowercase SHA-256")


def _reject_aliases(value: Any, path: str = "contract") -> None:
    if isinstance(value, dict):
        for raw_key, child in value.items():
            key = str(raw_key)
            if key in FORBIDDEN_ALIASES:
                raise ValidationError(f"forbidden legacy field at {path}.{key}")
            _reject_aliases(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_aliases(child, f"{path}[{index}]")


def _reject_test_requests(value: Any, path: str = "contract") -> None:
    risky = {"score_test", "test_scoring", "evaluate_test", "use_test", "load_test_labels"}
    split_keys = {"split", "evaluation_split", "eval_split", "score_split"}
    split_list_keys = {"splits", "training_splits", "evaluation_splits", "allowed_splits"}
    if isinstance(value, dict):
        for raw_key, child in value.items():
            key, child_path = str(raw_key).lower(), f"{path}.{raw_key}"
            if key in risky and child is True:
                raise ValidationError(f"test request denied at {child_path}")
            if key in split_keys and str(child).lower() == "test":
                raise ValidationError(f"test split denied at {child_path}")
            if key in split_list_keys:
                entries = child if isinstance(child, list) else [child]
                if any(str(entry).lower() == "test" for entry in entries):
                    raise ValidationError(f"test split denied at {child_path}")
            _reject_test_requests(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_test_requests(child, f"{path}[{index}]")


def _validate_common(contract_type: str, document: dict[str, Any]) -> None:
    if document.get("contract_type") != contract_type:
        raise ValidationError(
            f"contract_type must be {contract_type!r}, got {document.get('contract_type')!r}"
        )
    if not isinstance(document.get("schema_version"), int) or document["schema_version"] < 1:
        raise ValidationError("schema_version must be a positive integer")
    experiment_id = document.get("experiment_id")
    if not isinstance(experiment_id, str) or not EXPERIMENT_ID.fullmatch(experiment_id):
        raise ValidationError("experiment_id must start with exp- or exp_")
    sha_field = {
        "experiment_spec": "approved_against_commit_sha",
        "feature_proposal": "approved_against_commit_sha",
        "model_proposal": "approved_against_commit_sha",
        "decision_request": "approved_against_commit_sha",
        "run_manifest": "commit_sha",
        "metrics": "commit_sha",
        "final_approval": "commit_sha",
    }[contract_type]
    _validate_sha(document.get(sha_field), sha_field)
    if contract_type in {"feature_proposal", "model_proposal"}:
        _validate_sha(
            document.get("implementation_commit_sha"),
            "implementation_commit_sha",
            optional=True,
        )
    _reject_aliases(document)


def _validate_experiment_spec(document: dict[str, Any]) -> None:
    if document.get("author_role") != "A":
        raise ValidationError("experiment_spec author_role must be A")
    if document["status"] not in {"PROPOSED", "APPROVED_FOR_IMPLEMENTATION"}:
        raise ValidationError("unsupported experiment status")
    if not isinstance(document["hypothesis"], str) or not document["hypothesis"].strip():
        raise ValidationError("hypothesis must be non-empty")
    task = _require_object(document["task"], "task")
    if task.get("ranking_scope") != "within_user" or task.get("label") != "long_view":
        raise ValidationError("task must preserve within_user ranking and long_view")
    if task.get("evaluation_split") != "valid" or task.get("test_access_allowed") is not False:
        raise ValidationError("ordinary experiments must be valid-only with test denied")
    if int(task.get("maximum_development_date", 99999999)) > VALID_END:
        raise ValidationError("maximum_development_date exceeds 20220428")
    if task.get("primary_definition") != "mean(GAUC,nDCG@5)":
        raise ValidationError("primary metric definition changed")
    baseline = _require_object(document["baseline"], "baseline")
    if not isinstance(baseline.get("baseline_experiment_id"), str):
        raise ValidationError("baseline_experiment_id is required")
    if not isinstance(document["implementation_config"], str) or not document["implementation_config"]:
        raise ValidationError("implementation_config is required")
    if not isinstance(document["max_runtime_seconds"], int) or not 1 <= document["max_runtime_seconds"] <= 3600:
        raise ValidationError("max_runtime_seconds must be between 1 and 3600")
    if document["automatic_repair_attempts"] not in {0, 1}:
        raise ValidationError("automatic_repair_attempts must be 0 or 1")


def _validate_feature_proposal(document: dict[str, Any]) -> None:
    if document.get("author_role") != "C":
        raise ValidationError("feature_proposal author_role must be C")
    review = _require_object(document["leakage_review"], "leakage_review")
    if review.get("uses_future_information") is not False:
        raise ValidationError("feature proposal uses future information")
    if review.get("uses_test_information") is not False:
        raise ValidationError("feature proposal uses test information")


def _validate_model_proposal(document: dict[str, Any]) -> None:
    if document.get("author_role") != "D":
        raise ValidationError("model_proposal author_role must be D")
    if document.get("model_family") != "factorization_machine":
        raise ValidationError("model family change is not approved")
    _require_object(document["objective"], "objective")
    _require_object(document["sampling"], "sampling")
    _require_object(document["hyperparameters"], "hyperparameters")


def _validate_hash_map(value: Any, path: str) -> None:
    mapping = _require_object(value, path)
    if not mapping:
        raise ValidationError(f"{path} must not be empty")
    for name, digest in mapping.items():
        _validate_sha256(digest, f"{path}.{name}")


def _validate_run_manifest(document: dict[str, Any]) -> None:
    if document["status"] not in {"completed", "failed", "stopped"}:
        raise ValidationError("run_manifest status must be completed, failed, or stopped")
    if not isinstance(document["worktree_clean"], bool):
        raise ValidationError("worktree_clean must be boolean")
    if document["executor_role"] != "B":
        raise ValidationError("run_manifest executor_role must be B")
    if document.get("run_variant") not in {None, "baseline", "candidate"}:
        raise ValidationError("run_variant must be baseline or candidate")
    if document["status"] == "completed" and document.get("mode") != "valid-only":
        raise ValidationError("completed run mode must be valid-only")
    max_batches = document.get("max_batches")
    if max_batches is not None and (
        isinstance(max_batches, bool) or not isinstance(max_batches, int) or max_batches < 1
    ):
        raise ValidationError("max_batches must be null or a positive integer")
    commands = _require_list(document["commands"], "commands")
    if not commands or not all(isinstance(command, str) and command.strip() for command in commands):
        raise ValidationError("commands must be a non-empty array of strings")
    if not isinstance(document["dev_max_date"], int) or document["dev_max_date"] > VALID_END:
        if document["status"] == "completed":
            raise ValidationError("completed run requires dev_max_date <= 20220428")
    _require_object(document["config"], "config")
    data = _require_object(document["data"], "data")
    if data.get("split") != "valid":
        raise ValidationError("run manifest data.split must be valid")
    artifacts = _require_list(document["artifacts"], "artifacts")
    artifact_paths: set[str] = set()
    artifact_hashes: dict[str, str] = {}
    for index, artifact in enumerate(artifacts):
        item = _require_object(artifact, f"artifacts[{index}]")
        raw_path = item.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            raise ValidationError(f"artifacts[{index}].path is required")
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
            raise ValidationError(
                f"artifacts[{index}].path must be a normalized relative path"
            )
        if raw_path in artifact_paths:
            raise ValidationError(f"duplicate artifact path: {raw_path}")
        artifact_paths.add(raw_path)
        _validate_sha256(item.get("sha256"), f"artifacts[{index}].sha256")
        artifact_hashes[raw_path] = item["sha256"]
    if document["status"] == "completed":
        if document["worktree_clean"] is not True:
            raise ValidationError("completed run must record worktree_clean=true")
        for field in (
            "experiment_spec_hash", "config_input_hash", "config_hash", "data_hash",
            "prediction_hash", "checkpoint_hash",
        ):
            _validate_sha256(document[field], field)
        if document["run_variant"] not in {"baseline", "candidate"}:
            raise ValidationError("completed run requires baseline or candidate run_variant")
        if document.get("objective") not in SUPPORTED_OBJECTIVES:
            raise ValidationError("completed run requires a supported objective")
        if "max_batches" not in document:
            raise ValidationError("completed run requires max_batches runtime input")
        _validate_hash_map(document["protected_hashes"], "protected_hashes")
        missing_artifacts = REQUIRED_COMPLETED_ARTIFACTS.difference(artifact_paths)
        if missing_artifacts:
            raise ValidationError(
                "completed run is missing required artifacts: "
                + ", ".join(sorted(missing_artifacts))
            )
        extra_artifacts = artifact_paths.difference(REQUIRED_COMPLETED_ARTIFACTS)
        if extra_artifacts:
            raise ValidationError(
                "completed run has unexpected artifacts: "
                + ", ".join(sorted(extra_artifacts))
            )
        if document["config_hash"] != stable_json_hash(document["config"]):
            raise ValidationError("config_hash does not match run_manifest.config")
        if document["prediction_hash"] != artifact_hashes["valid_predictions.csv"]:
            raise ValidationError(
                "prediction_hash must match the valid_predictions.csv artifact hash"
            )
        if document["checkpoint_hash"] != artifact_hashes["checkpoint.npz"]:
            raise ValidationError(
                "checkpoint_hash must match the checkpoint.npz artifact hash"
            )


def _normalized_repository_file(
    raw_path: Any, repo_root: Path, required_directory: str, label: str,
) -> Path:
    if not isinstance(raw_path, str) or not raw_path:
        raise ValidationError(f"{label} must be a repository-relative path")
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
        or not posix_path.parts
        or posix_path.parts[0] != required_directory
    ):
        raise ValidationError(
            f"{label} must be a normalized path below {required_directory}/"
        )
    root = repo_root.resolve()
    candidate = root.joinpath(*posix_path.parts)
    current = root
    try:
        for part in posix_path.parts:
            current = current / part
            metadata = os.lstat(current)
            if stat.S_ISLNK(metadata.st_mode):
                raise ValidationError(f"{label} must not traverse a symlink")
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except ValidationError:
        raise
    except (OSError, ValueError) as exc:
        raise ValidationError(f"{label} is missing or escapes the repository") from exc
    if not stat.S_ISREG(os.lstat(resolved).st_mode):
        raise ValidationError(f"{label} must be an ordinary repository file")
    return resolved


def _read_repository_json_snapshot(path: Path, label: str) -> tuple[Any, str]:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        initial_path = os.lstat(path)
    except OSError as exc:
        raise ValidationError(f"{label} disappeared before reading") from exc
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ValidationError(f"cannot safely open {label}: {exc}") from exc
    try:
        with os.fdopen(descriptor, "rb") as handle:
            bound_path = os.lstat(path)
            before = os.fstat(handle.fileno())
            raw = handle.read()
            after = os.fstat(handle.fileno())
            path_after = os.lstat(path)
    except OSError as exc:
        raise ValidationError(f"cannot read {label}: {exc}") from exc
    if _artifact_signature(before) != _artifact_signature(after):
        raise ValidationError(f"{label} changed while reading")
    if (
        stat.S_ISLNK(bound_path.st_mode)
        or not stat.S_ISREG(bound_path.st_mode)
        or _artifact_signature(initial_path) != _artifact_signature(bound_path)
        or _artifact_signature(bound_path) != _artifact_signature(path_after)
        or _artifact_identity(bound_path) != _artifact_identity(before)
        or _artifact_identity(path_after) != _artifact_identity(after)
    ):
        raise ValidationError(f"{label} path changed while reading")
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"invalid JSON in {label}: {exc}") from exc
    return document, hashlib.sha256(raw).hexdigest()


def validate_approved_run_route(
    document: dict[str, Any], repo_root: Path | None = None,
) -> None:
    """Bind completed evidence to the approved spec and repository config bytes."""

    repo_root = (repo_root or Path(__file__).resolve().parents[1]).resolve()
    spec_path = _normalized_repository_file(
        document.get("experiment_spec_path"), repo_root, "experiments",
        "experiment_spec_path",
    )
    spec, spec_hash = _read_repository_json_snapshot(spec_path, "experiment spec")
    if spec_hash != document.get("experiment_spec_hash"):
        raise ValidationError("experiment_spec_hash does not match approved spec bytes")
    validate_contract("experiment_spec", spec)
    if spec.get("status") != "APPROVED_FOR_IMPLEMENTATION":
        raise ValidationError("experiment spec is not APPROVED_FOR_IMPLEMENTATION")
    if spec.get("experiment_id") != document.get("experiment_id"):
        raise ValidationError("manifest experiment_id does not match approved spec")

    variant = document.get("run_variant")
    if variant == "candidate":
        expected_config = spec.get("implementation_config")
    elif variant == "baseline":
        baseline = _require_object(spec.get("baseline"), "experiment_spec.baseline")
        expected_config = baseline.get("approved_config")
    else:
        raise ValidationError("run_variant must be baseline or candidate")
    if document.get("config_path") != expected_config:
        raise ValidationError(f"{variant} config_path does not match approved spec route")
    config_path = _normalized_repository_file(
        document.get("config_path"), repo_root, "configs", "config_path"
    )
    raw_config, config_input_hash = _read_repository_json_snapshot(
        config_path, "approved config"
    )
    if config_input_hash != document.get("config_input_hash"):
        raise ValidationError("config_input_hash does not match approved config bytes")
    raw_config = _require_object(raw_config, "approved config")
    validate_approved_run_semantics(document, spec, raw_config)
    rebuilt = {
        **raw_config,
        "resolved_run": {
            "experiment_id": document.get("experiment_id"),
            "run_variant": variant,
            "seed": document.get("seed"),
            "max_batches": document.get("max_batches"),
            "mode": document.get("mode"),
        },
    }
    if rebuilt != document.get("config"):
        raise ValidationError(
            "run_manifest.config cannot be rebuilt from approved config and runtime inputs"
        )
    if stable_json_hash(rebuilt) != document.get("config_hash"):
        raise ValidationError("config_hash does not match rebuilt resolved config")


def validate_approved_run_semantics(
    document: dict[str, Any], spec: dict[str, Any], raw_config: dict[str, Any],
) -> None:
    """Cross-check scientific/runtime identity after route bytes are bound."""

    if spec.get("author_role") != "A":
        raise ValidationError("approved experiment spec author_role must be A")
    variant = document.get("run_variant")
    if variant == "candidate":
        expected_objective = spec.get("objective")
    elif variant == "baseline":
        expected_objective = "pointwise_binary_cross_entropy"
        baseline = _require_object(spec.get("baseline"), "experiment_spec.baseline")
        if raw_config.get("contract_type") != "approved_config":
            raise ValidationError("baseline config contract_type must be approved_config")
        if raw_config.get("status") != "APPROVED":
            raise ValidationError("baseline config status must be APPROVED")
        if not isinstance(raw_config.get("schema_version"), int):
            raise ValidationError("baseline config schema_version must be an integer")
        _validate_sha(
            raw_config.get("approved_against_commit_sha"),
            "baseline config approved_against_commit_sha",
        )
        if raw_config.get("experiment_id") != baseline.get("baseline_experiment_id"):
            raise ValidationError(
                "baseline config experiment_id does not match the experiment spec"
            )
    else:
        raise ValidationError("run_variant must be baseline or candidate")
    if expected_objective not in SUPPORTED_OBJECTIVES:
        raise ValidationError("approved experiment objective is unsupported")
    if document.get("objective") != expected_objective:
        raise ValidationError("manifest objective does not match the approved route")
    objective = _require_object(raw_config.get("objective"), "approved config.objective")
    if objective.get("name") != expected_objective:
        raise ValidationError("approved config objective does not match the approved route")

    training = _require_object(raw_config.get("training"), "approved config.training")
    configured_seed = training.get("seed")
    if isinstance(configured_seed, bool) or not isinstance(configured_seed, int):
        raise ValidationError("approved config training.seed must be an integer")
    if document.get("seed") != configured_seed:
        raise ValidationError("manifest seed does not match approved config training.seed")
    if document.get("mode") != "valid-only":
        raise ValidationError("completed approved evidence must use valid-only mode")

    configured_max_batches = training.get("max_batches")
    if configured_max_batches is not None and (
        isinstance(configured_max_batches, bool)
        or not isinstance(configured_max_batches, int)
        or configured_max_batches < 1
    ):
        raise ValidationError(
            "approved config training.max_batches must be null or a positive integer"
        )
    if (
        configured_max_batches is not None
        and document.get("max_batches") != configured_max_batches
    ):
        raise ValidationError(
            "manifest max_batches does not match approved config training.max_batches"
        )


def _artifact_signature(metadata: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        int(metadata.st_dev), int(metadata.st_ino), int(metadata.st_mode),
        int(metadata.st_size), int(metadata.st_mtime_ns), int(metadata.st_ctime_ns),
    )


def _artifact_identity(metadata: os.stat_result) -> tuple[int, int, int]:
    return (int(metadata.st_dev), int(metadata.st_ino), int(metadata.st_mode))


def _read_open_artifact(
    handle: BinaryIO, path: Path, *, capture_bytes: bool,
) -> tuple[str, bytes | None]:
    """Hash bytes from one already-bound handle and reject in-place changes."""

    try:
        before = _artifact_signature(os.fstat(handle.fileno()))
        digest = hashlib.sha256()
        captured = bytearray() if capture_bytes else None
        handle.seek(0)
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
            if captured is not None:
                captured.extend(block)
        after = _artifact_signature(os.fstat(handle.fileno()))
    except OSError as exc:
        raise ValidationError(f"cannot read artifact safely: {path.name}: {exc}") from exc
    if before != after:
        raise ValidationError(f"artifact changed while hashing: {path.name}")
    return digest.hexdigest(), None if captured is None else bytes(captured)


def _assert_artifact_binding(
    path: Path, handle: BinaryIO,
    path_signature: tuple[int, int, int, int, int, int],
    handle_signature: tuple[int, int, int, int, int, int],
) -> None:
    try:
        current_path = os.lstat(path)
        current_handle = os.fstat(handle.fileno())
    except OSError as exc:
        raise ValidationError(f"artifact binding changed for {path.name}: {exc}") from exc
    if (
        stat.S_ISLNK(current_path.st_mode)
        or not stat.S_ISREG(current_path.st_mode)
        or _artifact_signature(current_path) != path_signature
        or _artifact_signature(current_handle) != handle_signature
    ):
        raise ValidationError(f"artifact path changed during validation: {path.name}")


def validate_artifact_files(document: dict[str, Any], artifact_root: Path) -> None:
    """Verify every declared artifact against bytes below the run directory."""
    validate_contract("run_manifest", document)
    if document.get("status") != "completed":
        raise ValidationError(
            "only a completed run_manifest can be accepted as artifact evidence"
        )
    validate_approved_run_route(document)
    root = artifact_root.resolve()
    resolved_config_bytes: bytes | None = None
    bindings: list[
        tuple[
            Path, BinaryIO, tuple[int, int, int, int, int, int],
            tuple[int, int, int, int, int, int], str,
        ]
    ] = []
    with ExitStack() as stack:
        for index, artifact in enumerate(document["artifacts"]):
            relative = Path(artifact["path"])
            candidate = root / relative
            try:
                candidate.relative_to(root)
                path_metadata = os.lstat(candidate)
            except ValueError as exc:
                raise ValidationError(
                    f"artifacts[{index}].path escapes the run directory"
                ) from exc
            except OSError as exc:
                raise ValidationError(
                    f"artifact file is missing: {relative.as_posix()}"
                ) from exc
            if stat.S_ISLNK(path_metadata.st_mode) or not stat.S_ISREG(path_metadata.st_mode):
                raise ValidationError(
                    "artifact path must name an ordinary file, not a symlink: "
                    f"{relative.as_posix()}"
                )
            flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
            try:
                descriptor = os.open(candidate, flags)
            except OSError as exc:
                raise ValidationError(
                    f"cannot safely open artifact: {relative.as_posix()}: {exc}"
                ) from exc
            try:
                opened_handle = os.fdopen(descriptor, "rb")
            except BaseException:
                os.close(descriptor)
                raise
            handle = stack.enter_context(opened_handle)
            try:
                opened_metadata = os.fstat(handle.fileno())
                bound_path_metadata = os.lstat(candidate)
            except OSError as exc:
                raise ValidationError(
                    f"artifact path changed while opening: {relative.as_posix()}: {exc}"
                ) from exc
            opened_signature = _artifact_signature(opened_metadata)
            bound_path_signature = _artifact_signature(bound_path_metadata)
            if (
                not stat.S_ISREG(opened_metadata.st_mode)
                or _artifact_identity(path_metadata) != _artifact_identity(opened_metadata)
                or _artifact_identity(bound_path_metadata)
                != _artifact_identity(opened_metadata)
            ):
                raise ValidationError(
                    f"artifact path changed while opening: {relative.as_posix()}"
                )
            capture = relative.as_posix() == "resolved_config.json"
            actual, captured = _read_open_artifact(
                handle, candidate, capture_bytes=capture
            )
            second_actual, second_captured = _read_open_artifact(
                handle, candidate, capture_bytes=capture
            )
            if actual != second_actual or captured != second_captured:
                raise ValidationError(
                    f"artifact bytes changed during validation: {relative.as_posix()}"
                )
            if actual != artifact["sha256"]:
                raise ValidationError(
                    f"artifact hash mismatch for {relative.as_posix()}: "
                    f"expected {artifact['sha256']}, observed {actual}"
                )
            if capture:
                resolved_config_bytes = captured
            bindings.append(
                (
                    candidate, handle, bound_path_signature, opened_signature,
                    artifact["sha256"],
                )
            )

        for candidate, handle, path_signature, handle_signature, _ in bindings:
            _assert_artifact_binding(
                candidate, handle, path_signature, handle_signature
            )

        if resolved_config_bytes is None:
            raise ValidationError("resolved_config.json bytes were not captured")
        try:
            resolved_config = json.loads(resolved_config_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValidationError(f"invalid JSON in resolved_config.json: {exc}") from exc
        resolved_config_hash = stable_json_hash(resolved_config)
        if resolved_config_hash != stable_json_hash(document["config"]):
            raise ValidationError(
                "resolved_config.json content must equal run_manifest.config"
            )
        if resolved_config_hash != document["config_hash"]:
            raise ValidationError(
                "resolved_config.json canonical hash must equal run_manifest.config_hash"
            )
        for (
            candidate, handle, path_signature, handle_signature, expected_hash,
        ) in bindings:
            _assert_artifact_binding(
                candidate, handle, path_signature, handle_signature
            )
            final_hash, _ = _read_open_artifact(
                handle, candidate, capture_bytes=False
            )
            if final_hash != expected_hash:
                raise ValidationError(
                    f"artifact bytes changed during validation: {candidate.name}"
                )
            _assert_artifact_binding(
                candidate, handle, path_signature, handle_signature
            )
        return


def _validate_metrics(document: dict[str, Any]) -> None:
    if document["evaluator_role"] != "E":
        raise ValidationError("metrics evaluator_role must be E")
    if document["split"] != "valid":
        raise ValidationError("ordinary metrics split must be valid")
    if document["status"] not in {"completed", "failed"}:
        raise ValidationError("metrics status must be completed or failed")
    if not isinstance(document["worktree_clean"], bool):
        raise ValidationError("worktree_clean must be boolean")
    metrics = _require_object(document["metrics"], "metrics")
    if document["status"] == "completed":
        values = [metrics.get("GAUC"), metrics.get("nDCG@5"), metrics.get("primary")]
        if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in values):
            raise ValidationError("completed metrics must contain finite GAUC/nDCG@5/primary")
        if not math.isclose(float(values[2]), (float(values[0]) + float(values[1])) / 2.0):
            raise ValidationError("primary must be the arithmetic mean of GAUC and nDCG@5")
        _validate_hash_map(document["protected_hashes"], "protected_hashes")


def _validate_decision_request(document: dict[str, Any]) -> None:
    if document["requested_by_role"] not in {"A", "B", "C", "D", "E"}:
        raise ValidationError("requested_by_role is invalid")
    if document["automation_paused"] is not True or document["status"] != "pending_human":
        raise ValidationError("decision request must pause automation and be pending_human")
    if not isinstance(document["summary"], str) or not document["summary"].strip():
        raise ValidationError("decision request summary is required")


def _validate_final_approval(document: dict[str, Any]) -> None:
    if not isinstance(document["approved"], bool):
        raise ValidationError("approved must be boolean")
    if not isinstance(document["approved_by"], str) or not document["approved_by"].strip():
        raise ValidationError("approved_by must identify a human")
    _validate_hash_map(document["protected_hashes"], "protected_hashes")


VALIDATORS = {
    "experiment_spec": _validate_experiment_spec,
    "feature_proposal": _validate_feature_proposal,
    "model_proposal": _validate_model_proposal,
    "run_manifest": _validate_run_manifest,
    "metrics": _validate_metrics,
    "decision_request": _validate_decision_request,
    "final_approval": _validate_final_approval,
}


def validate_contract(contract_type: str, document: Any) -> None:
    canonical = _canonical_type(contract_type)
    if canonical not in REQUIRED_FIELDS:
        raise ValidationError(f"unknown contract type: {contract_type}")
    root = _require_object(document, "contract")
    missing = [field for field in REQUIRED_FIELDS[canonical] if field not in root]
    if missing:
        raise ValidationError(f"missing required fields: {', '.join(missing)}")
    _validate_common(canonical, root)
    _reject_test_requests(root)
    VALIDATORS[canonical](root)


def parse_args() -> argparse.Namespace:
    choices = tuple(REQUIRED_FIELDS) + tuple(ALIASES)
    parser = argparse.ArgumentParser(description="Validate a canonical team JSON contract.")
    parser.add_argument("--type", required=True, choices=choices)
    parser.add_argument("--path", required=True, type=Path)
    parser.add_argument(
        "--artifact-root",
        type=Path,
        help="Run directory used to verify completed run-manifest artifact bytes.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        document = read_json(args.path)
        validate_contract(args.type, document)
        if _canonical_type(args.type) == "run_manifest" and document.get("status") == "completed":
            validate_artifact_files(document, args.artifact_root or args.path.resolve().parent)
    except ValidationError as exc:
        print("CONTRACT=FAIL", file=sys.stderr)
        print(f"ERROR={exc}", file=sys.stderr)
        return 1
    print("CONTRACT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
