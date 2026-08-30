from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import json
import math
import os
import platform
import re
import shlex
import stat
import subprocess
import sys
import tempfile
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models import FactorizationMachine
from src.training import ResolvedTrainingConfig, fit_pointwise
from src.training.bpr import PairCoverage, fit_bpr_epoch
from src.training.checkpoint import save_checkpoint
from tools.common import (
    OFFICIAL_LOG_FILES,
    REQUIRED_STATIC_FILES,
    ValidationError,
    read_json,
    sha256_file,
    stable_json_hash,
    write_json,
)
from tools.preflight import inspect_data
from tools.project_security import verify_protected_files
from tools.validate_contract import (
    validate_approved_run_semantics,
    validate_artifact_files,
    validate_contract,
)


FULL_SHA = re.compile(r"[0-9a-f]{40}")
FULL_SHA256 = re.compile(r"[0-9a-f]{64}")
LEGACY_RUNNER_FIELDS = {"k", "lr", "batch", "max_epochs"}
SUPPORTED_OBJECTIVES = {"pointwise_binary_cross_entropy", "same_user_bpr"}


class TransientInfrastructureError(RuntimeError):
    """An explicitly classified infrastructure error eligible for one retry."""


class RunTimeout(ValidationError):
    """Raised when the approved wall-clock budget is exhausted."""


@dataclass(frozen=True)
class DataSnapshot:
    """Content hashes that bind one inspected/loaded development-data snapshot."""

    data_hash: str
    manifest_hash: str | None
    source_hashes: tuple[tuple[str, str], ...]


def ensure_aligned_lengths(*arrays: Sequence[Any]) -> int:
    lengths = [len(array) for array in arrays]
    if not lengths or len(set(lengths)) != 1:
        raise ValidationError(f"array length mismatch: {lengths}")
    return lengths[0]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _git_state(repo_root: Path) -> tuple[str, bool]:
    try:
        commit_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        worktree_clean = not bool(subprocess.run(
            ["git", "status", "--porcelain"], cwd=repo_root, check=True,
            capture_output=True, text=True,
        ).stdout.strip())
        return commit_sha, worktree_clean
    except (OSError, subprocess.CalledProcessError):
        return "0" * 40, False


def _git_is_ancestor(repo_root: Path, ancestor: str, descendant: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=repo_root, capture_output=True, text=True,
        )
    except OSError:
        return False
    return result.returncode == 0


def _read_json_snapshot(path: Path) -> tuple[Any, str]:
    """Parse JSON from exactly the bytes represented by the returned digest."""

    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValidationError(f"cannot read JSON file {path}: {exc}") from exc
    digest = hashlib.sha256(raw).hexdigest()
    try:
        return json.loads(raw.decode("utf-8")), digest
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"invalid JSON in {path}: {exc}") from exc


def _data_signature(metadata: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        int(metadata.st_dev), int(metadata.st_ino), int(metadata.st_mode),
        int(metadata.st_size),
        int(metadata.st_mtime_ns), int(metadata.st_ctime_ns),
    )


def _data_identity(metadata: os.stat_result) -> tuple[int, int, int]:
    return (int(metadata.st_dev), int(metadata.st_ino), int(metadata.st_mode))


def _copy_bound_data_file(path: Path, destination: Path | None = None) -> str:
    """Hash/copy bytes through one no-follow handle bound to a regular file."""

    try:
        path_metadata = os.lstat(path)
    except OSError as exc:
        raise ValidationError(f"missing data source: {path}") from exc
    if stat.S_ISLNK(path_metadata.st_mode) or not stat.S_ISREG(path_metadata.st_mode):
        raise ValidationError(f"data source must be an ordinary file: {path}")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ValidationError(f"cannot safely open data source {path}: {exc}") from exc
    digest = hashlib.sha256()
    destination_created = False
    try:
        try:
            source_handle = os.fdopen(descriptor, "rb")
        except BaseException:
            os.close(descriptor)
            raise
        with source_handle as source:
            opened = os.fstat(source.fileno())
            opened_signature = _data_signature(opened)
            try:
                bound_path = os.lstat(path)
            except OSError as exc:
                raise ValidationError(
                    f"data source disappeared while opening: {path}"
                ) from exc
            bound_path_signature = _data_signature(bound_path)
            if (
                not stat.S_ISREG(opened.st_mode)
                or _data_identity(path_metadata) != _data_identity(opened)
                or _data_identity(bound_path) != _data_identity(opened)
            ):
                raise ValidationError(f"data source changed while opening: {path}")
            destination_handle = (
                destination.open("xb") if destination is not None else None
            )
            destination_created = destination_handle is not None
            try:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(block)
                    if destination_handle is not None:
                        destination_handle.write(block)
            finally:
                if destination_handle is not None:
                    destination_handle.close()
            if _data_signature(os.fstat(source.fileno())) != opened_signature:
                raise ValidationError(f"data source changed while reading: {path}")
            try:
                final_path = os.lstat(path)
            except OSError as exc:
                raise ValidationError(f"data source disappeared while reading: {path}") from exc
            if _data_signature(final_path) != bound_path_signature:
                raise ValidationError(f"data source path changed while reading: {path}")
    except BaseException:
        if destination_created and destination is not None:
            try:
                destination.unlink()
            except OSError:
                pass
        raise
    return digest.hexdigest()


def _stable_data_file_hash(path: Path) -> str:
    return _copy_bound_data_file(path)


def _safe_manifest_source(data_dir: Path, name: Any) -> Path:
    if not isinstance(name, str) or not name or name in {".", ".."}:
        raise ValidationError("dataset_manifest files keys must be non-empty file names")
    if "\\" in name or Path(name).name != name:
        raise ValidationError(f"dataset_manifest source path must be a direct file name: {name!r}")
    candidate = data_dir / name
    try:
        candidate.resolve().relative_to(data_dir.resolve())
    except (OSError, ValueError) as exc:
        raise ValidationError(f"dataset_manifest source escapes data directory: {name!r}") from exc
    return candidate


def _capture_data_snapshot(data_dir: Path) -> DataSnapshot:
    """Bind the manifest and every declared source to verified on-disk bytes."""

    data_dir = data_dir.resolve()
    required = set((*OFFICIAL_LOG_FILES, *REQUIRED_STATIC_FILES))
    manifest_path = data_dir / "dataset_manifest.json"
    manifest_hash: str | None = None
    declared_hashes: dict[str, str] | None = None
    if manifest_path.is_file():
        manifest, manifest_hash = _read_json_snapshot(manifest_path)
        if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), dict):
            raise ValidationError("dataset_manifest.json must contain a files object")
        files = manifest["files"]
        missing = required.difference(files)
        if missing:
            raise ValidationError(
                "dataset_manifest.json is missing required sources: "
                + ", ".join(sorted(missing))
            )
        declared_hashes = {}
        for name, entry in files.items():
            source = _safe_manifest_source(data_dir, name)
            if not isinstance(entry, dict):
                raise ValidationError(f"dataset_manifest files[{name!r}] must be an object")
            expected = entry.get("sha256")
            if not isinstance(expected, str) or not FULL_SHA256.fullmatch(expected):
                raise ValidationError(
                    f"dataset_manifest files[{name!r}].sha256 must be lowercase SHA-256"
                )
            actual = _stable_data_file_hash(source)
            if actual != expected:
                raise ValidationError(
                    f"dataset source hash mismatch for {name}: expected {expected}, observed {actual}"
                )
            declared_hashes[name] = actual
        _, manifest_hash_after = _read_json_snapshot(manifest_path)
        if manifest_hash_after != manifest_hash:
            raise ValidationError("dataset_manifest.json changed while sources were verified")
        data_hash = manifest_hash
    else:
        declared_hashes = {
            name: _stable_data_file_hash(data_dir / name)
            for name in sorted(required)
        }
        data_hash = stable_json_hash([
            {"path": name, "sha256": digest}
            for name, digest in sorted(declared_hashes.items())
        ])
    return DataSnapshot(
        data_hash=data_hash,
        manifest_hash=manifest_hash,
        source_hashes=tuple(sorted(declared_hashes.items())),
    )


def _assert_data_snapshot(data_dir: Path, expected: DataSnapshot, phase: str) -> None:
    observed = _capture_data_snapshot(data_dir)
    if observed != expected:
        raise ValidationError(f"development data changed {phase}")


def _materialize_data_snapshot(
    data_dir: Path, expected: DataSnapshot, destination: Path,
) -> DataSnapshot:
    """Copy exactly the verified input bytes into a private execution snapshot."""

    destination.mkdir(parents=True, exist_ok=False)
    expected_sources = dict(expected.source_hashes)
    required = sorted((*OFFICIAL_LOG_FILES, *REQUIRED_STATIC_FILES))
    for name in required:
        expected_hash = expected_sources[name]
        source = _safe_manifest_source(data_dir.resolve(), name)
        actual = _copy_bound_data_file(source, destination / name)
        if actual != expected_hash:
            raise ValidationError(
                f"development data changed before execution snapshot: {name}"
            )
    observed = _capture_data_snapshot(destination)
    expected_required_hashes = tuple(
        (name, expected_sources[name]) for name in required
    )
    if observed.source_hashes != expected_required_hashes:
        raise ValidationError("materialized development-data snapshot is inconsistent")
    return observed


def _data_hash(data_dir: Path) -> str:
    return _capture_data_snapshot(data_dir).data_hash


def _reject_legacy_runner_fields(value: Any, path: str = "config") -> None:
    if isinstance(value, dict):
        for raw_key, child in value.items():
            key = str(raw_key)
            if key in LEGACY_RUNNER_FIELDS:
                raise ValidationError(
                    f"legacy runner field {path}.{key} is forbidden; use canonical fields"
                )
            _reject_legacy_runner_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_legacy_runner_fields(child, f"{path}[{index}]")


def _settings(
    config: dict[str, Any], *, seed: int | None = None,
    max_batches: int | None = None,
    synthetic_smoke: bool = False,
) -> dict[str, Any]:
    _reject_legacy_runner_fields(config)
    model, training, objective = (
        config.get("model"), config.get("training"), config.get("objective")
    )
    if not isinstance(model, dict):
        raise ValidationError("model must be an object using canonical fields")
    if not isinstance(training, dict):
        raise ValidationError("training must be an object using canonical fields")
    if not isinstance(objective, dict):
        raise ValidationError("objective must be an object")
    unknown_model = set(model).difference({"name", "embedding_dim", "learning_rate", "l2"})
    unknown_training = set(training).difference(
        {"seed", "batch_size", "epochs", "patience", "max_batches"}
    )
    if unknown_model:
        raise ValidationError(f"unknown model fields: {sorted(unknown_model)}")
    if unknown_training:
        raise ValidationError(f"unknown training fields: {sorted(unknown_training)}")
    if model.get("name") != "factorization_machine":
        raise ValidationError("model.name must be factorization_machine")
    objective_name = objective.get("name")
    if objective_name not in SUPPORTED_OBJECTIVES:
        raise ValidationError(f"unsupported objective: {objective_name!r}")

    configured_seed = int(training.get("seed", 0))
    effective_seed = configured_seed if seed is None else int(seed)
    if seed is not None and effective_seed != configured_seed:
        raise ValidationError(
            f"CLI seed {effective_seed} does not match approved training.seed {configured_seed}"
        )
    configured_max_batches = training.get("max_batches")
    if configured_max_batches is not None and (
        isinstance(configured_max_batches, bool)
        or not isinstance(configured_max_batches, int)
        or configured_max_batches < 1
    ):
        raise ValidationError("training.max_batches must be null or a positive integer")
    if max_batches is not None and (
        isinstance(max_batches, bool) or not isinstance(max_batches, int) or max_batches < 1
    ):
        raise ValidationError("max_batches must be a positive integer")
    if synthetic_smoke:
        if max_batches is None:
            raise ValidationError("synthetic smoke requires an explicit --max-batches bound")
        effective_max_batches = max_batches
    else:
        if max_batches is not None and max_batches != configured_max_batches:
            raise ValidationError(
                "formal max-batches must exactly match approved training.max_batches"
            )
        effective_max_batches = configured_max_batches

    settings = {
        "model_name": "factorization_machine",
        "embedding_dim": int(model.get("embedding_dim", 16)),
        "learning_rate": float(model.get("learning_rate", 0.001)),
        "l2": float(model.get("l2", 1e-6)),
        "seed": effective_seed,
        "batch_size": int(training.get("batch_size", 8192)),
        "epochs": int(training.get("epochs", 40)),
        "patience": int(training.get("patience", 4)),
        "max_batches": None if effective_max_batches is None else int(effective_max_batches),
        "objective": str(objective_name),
        "negatives_per_positive": int(objective.get("negatives_per_positive", 1)),
    }
    if settings["embedding_dim"] < 1:
        raise ValidationError("embedding_dim must be positive")
    if settings["learning_rate"] <= 0 or settings["l2"] < 0:
        raise ValidationError("learning_rate must be positive and l2 non-negative")
    if settings["batch_size"] < 1 or settings["epochs"] < 1 or settings["patience"] < 1:
        raise ValidationError("batch_size, epochs, and patience must be positive")
    if settings["max_batches"] is not None and settings["max_batches"] < 1:
        raise ValidationError("max_batches must be positive when provided")
    if settings["negatives_per_positive"] < 1:
        raise ValidationError("negatives_per_positive must be positive")
    return settings


def _resolve_reference(repo_root: Path, reference: str) -> Path:
    path = Path(reference)
    return path.resolve() if path.is_absolute() else (repo_root / path).resolve()


def _display_path(path: Path, repo_root: Path, label: str) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return f"<{label}>/{path.name}"


def _require_repository_input(
    path: Path, repo_root: Path, required_directory: str, label: str,
) -> None:
    """Require formal spec/config evidence to be an ordinary tracked-tree input."""

    resolved = path.resolve()
    try:
        relative = resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ValidationError(f"{label} must be inside the repository") from exc
    if not relative.parts or relative.parts[0] != required_directory:
        raise ValidationError(f"{label} must be under {required_directory}/")
    if path.is_symlink() or not resolved.is_file():
        raise ValidationError(f"{label} must be an ordinary repository file")


def _validate_approved_inputs(
    spec: Any, config: Any, experiment_spec_path: Path, config_path: Path,
    repo_root: Path,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    validate_contract("experiment-spec", spec)
    if spec.get("status") != "APPROVED_FOR_IMPLEMENTATION":
        raise ValidationError("experiment spec is not APPROVED_FOR_IMPLEMENTATION")
    if spec.get("task", {}).get("test_access_allowed") is not False:
        raise ValidationError("ordinary experiment spec must explicitly deny test access")
    if not isinstance(config, dict):
        raise ValidationError("config root must be an object")
    candidate_path = _resolve_reference(repo_root, str(spec.get("implementation_config", "")))
    baseline = spec.get("baseline")
    if not isinstance(baseline, dict):
        raise ValidationError("experiment spec baseline must be an object")
    baseline_path = _resolve_reference(repo_root, str(baseline.get("approved_config", "")))
    actual_path = config_path.resolve()
    if actual_path == candidate_path:
        variant, expected_objective = "candidate", spec.get("objective")
    elif actual_path == baseline_path:
        variant = "baseline"
        objective = config.get("objective")
        if not isinstance(objective, dict):
            raise ValidationError("baseline config objective must be an object")
        expected_objective = objective.get("name")
    else:
        raise ValidationError(
            "--config must match experiment_spec.implementation_config or baseline.approved_config"
        )
    objective = config.get("objective")
    if not isinstance(objective, dict) or objective.get("name") != expected_objective:
        raise ValidationError(f"{variant} config objective must be {expected_objective!r}")
    return spec, config, variant


def _load_approved_inputs(
    experiment_spec_path: Path, config_path: Path, repo_root: Path,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    spec, _ = _read_json_snapshot(experiment_spec_path)
    config, _ = _read_json_snapshot(config_path)
    return _validate_approved_inputs(
        spec, config, experiment_spec_path, config_path, repo_root
    )


def _build_model(settings: dict[str, Any], feature_dim: int) -> FactorizationMachine:
    return FactorizationMachine(
        feature_dim=feature_dim,
        embedding_dim=settings["embedding_dim"],
        learning_rate=settings["learning_rate"],
        l2=settings["l2"],
        seed=settings["seed"],
    )


def _write_predictions(path: Path, rows: Sequence[Any], scores: Sequence[Any]) -> str:
    ensure_aligned_lengths(rows, scores)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["row_id", "user_id", "video_id", "score"])
        for row_id, (row, score) in enumerate(zip(rows, scores)):
            numeric = float(score)
            if not math.isfinite(numeric):
                raise ValidationError(f"non-finite score at row {row_id}")
            writer.writerow([row_id, row[1], row[2], format(numeric, ".17g")])
    return sha256_file(path)


def _json_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        key: (value.item() if hasattr(value, "item") else value)
        for key, value in metrics.items()
    }


def _check_deadline(deadline: float) -> None:
    if time.monotonic() > deadline:
        raise RunTimeout("run exceeded max_runtime_seconds")


def _train_pointwise(
    model: FactorizationMachine, X_train: Any, y_train: Any, X_valid: Any,
    metric: Callable[[Any], float], training: ResolvedTrainingConfig, deadline: float,
) -> tuple[list[dict[str, Any]], int, int, float, dict[str, Any]]:
    _check_deadline(deadline)
    result = fit_pointwise(model, X_train, y_train, X_valid, metric, training)
    _check_deadline(deadline)
    history = [
        {"epoch": index + 1, "train_loss": loss, "valid_primary": primary}
        for index, (loss, primary) in enumerate(
            zip(result.train_losses, result.validation_metrics)
        )
    ]
    batches = math.ceil(len(y_train) / training.batch_size)
    if training.max_batches is not None:
        batches = min(batches, training.max_batches)
    return history, result.epochs_ran * batches, result.best_epoch, result.best_metric, {}


def _train_bpr(
    model: FactorizationMachine, X_train: Any, y_train: Any,
    users_train: Sequence[str], X_valid: Any,
    validation_metrics: Callable[[Any], dict[str, Any]],
    training: ResolvedTrainingConfig, negatives_per_positive: int, deadline: float,
) -> tuple[list[dict[str, Any]], int, int, float, dict[str, Any]]:
    best_metric, best_epoch, best_state = float("-inf"), 0, None
    bad_epochs = batches_seen = 0
    history: list[dict[str, Any]] = []
    last_coverage: PairCoverage | None = None
    for epoch in range(training.epochs):
        _check_deadline(deadline)
        loss, coverage = fit_bpr_epoch(
            model, X_train, y_train, users_train, training,
            negatives_per_positive=negatives_per_positive, epoch=epoch,
        )
        last_coverage = coverage
        batches = math.ceil(coverage.pairs / training.batch_size)
        if training.max_batches is not None:
            batches = min(batches, training.max_batches)
        batches_seen += batches
        metrics = validation_metrics(model.predict_scores(X_valid))
        primary = float(metrics["primary"])
        if not math.isfinite(primary):
            raise ValidationError("validation primary must be finite")
        history.append({
            "epoch": epoch + 1, "train_loss": loss, "valid": metrics,
            "pair_count": coverage.pairs,
            "eligible_users": coverage.eligible_users,
            "total_users": coverage.total_users,
            "user_coverage": coverage.user_coverage,
        })
        if primary > best_metric + 1e-5:
            best_metric, best_epoch, best_state, bad_epochs = (
                primary, epoch + 1, model.state_dict(), 0
            )
        else:
            bad_epochs += 1
            if bad_epochs >= training.patience:
                break
    if best_state is None or last_coverage is None:
        raise ValidationError("BPR training did not produce a best checkpoint")
    model.load_state_dict(best_state)
    coverage_record = {
        "pair_count": last_coverage.pairs,
        "eligible_users": last_coverage.eligible_users,
        "total_users": last_coverage.total_users,
        "user_coverage": last_coverage.user_coverage,
    }
    return history, batches_seen, best_epoch, best_metric, coverage_record


def _execute_bound_snapshot(
    spec: dict[str, Any], config: dict[str, Any], variant: str,
    data_dir: Path, output_dir: Path, seed: int, max_batches: int | None,
    mode: str, data_snapshot: DataSnapshot, synthetic_smoke: bool = False,
) -> dict[str, Any]:
    _assert_data_snapshot(data_dir, data_snapshot, "before preflight inspection")
    preflight = inspect_data(data_dir, "experiment", {"spec": spec, "config": config})
    _assert_data_snapshot(data_dir, data_snapshot, "during preflight inspection")
    settings = _settings(
        config, seed=seed, max_batches=max_batches, synthetic_smoke=synthetic_smoke
    )
    try:
        starter_data = importlib.import_module("starter.data")
        starter_evaluate = importlib.import_module("starter.evaluate")
    except ImportError as exc:
        raise ValidationError("starter.data/evaluate are unavailable") from exc
    splits = starter_data.load(str(data_dir))
    _assert_data_snapshot(data_dir, data_snapshot, "while loading the training snapshot")
    if not isinstance(splits, dict) or "train" not in splits or "valid" not in splits:
        raise ValidationError("starter.data.load must return train and valid splits")
    if splits.get("test"):
        raise ValidationError("development data unexpectedly produced non-empty held-out rows")
    encoded, feature_dim = starter_data.encode(splits)
    X_train, y_train, users_train = encoded["train"]
    X_valid, y_valid, users_valid = encoded["valid"]
    ensure_aligned_lengths(X_train, y_train, users_train, splits["train"])
    ensure_aligned_lengths(X_valid, y_valid, users_valid, splits["valid"])
    try:
        import numpy as np
    except ImportError as exc:
        raise ValidationError("numpy is required by the approved model") from exc
    model = _build_model(settings, feature_dim)
    training = ResolvedTrainingConfig(
        seed=settings["seed"], batch_size=settings["batch_size"],
        epochs=1 if settings["max_batches"] is not None else settings["epochs"],
        patience=settings["patience"], max_batches=settings["max_batches"],
    )
    max_runtime_seconds = int(spec.get("max_runtime_seconds", 3600))
    if not 1 <= max_runtime_seconds <= 3600:
        raise ValidationError("max_runtime_seconds must be between 1 and 3600")
    deadline = time.monotonic() + max_runtime_seconds

    def valid_metrics(scores: Any) -> dict[str, Any]:
        ensure_aligned_lengths(scores, y_valid, users_valid)
        array = np.asarray(scores, dtype=float)
        if not np.isfinite(array).all():
            raise ValidationError("model produced NaN/Inf validation scores")
        return _json_metrics(starter_evaluate.evaluate(users_valid, y_valid, array))

    if settings["objective"] == "pointwise_binary_cross_entropy":
        history, batches_seen, best_epoch, best_primary, coverage = _train_pointwise(
            model, X_train, y_train, X_valid,
            lambda scores: float(valid_metrics(scores)["primary"]), training, deadline,
        )
    else:
        history, batches_seen, best_epoch, best_primary, coverage = _train_bpr(
            model, X_train, y_train, users_train, X_valid, valid_metrics, training,
            settings["negatives_per_positive"], deadline,
        )
    _check_deadline(deadline)
    final_scores = model.predict_scores(X_valid)
    ensure_aligned_lengths(final_scores, splits["valid"])
    metrics = valid_metrics(final_scores)
    prediction_path = output_dir / "valid_predictions.csv"
    prediction_hash = _write_predictions(prediction_path, splits["valid"], final_scores)
    resolved_config = {
        **config,
        "resolved_run": {
            "experiment_id": spec["experiment_id"], "run_variant": variant,
            "seed": seed, "max_batches": settings["max_batches"], "mode": mode,
        },
    }
    checkpoint_path = output_dir / "checkpoint.npz"
    save_checkpoint(
        checkpoint_path, model, config=resolved_config,
        epoch=best_epoch, best_metric=best_primary,
    )
    checkpoint_hash = sha256_file(checkpoint_path)
    history_path = output_dir / "training_history.json"
    write_json(history_path, history)
    runner_metrics_path = output_dir / "runner_metrics.json"
    write_json(runner_metrics_path, {
        "status": "PENDING_E_REVIEW", "split": "valid",
        "objective": settings["objective"], "metrics": metrics,
    })
    _assert_data_snapshot(data_dir, data_snapshot, "during execution")
    return {
        "experiment_id": spec["experiment_id"], "run_variant": variant,
        "objective": settings["objective"], "resolved_config": resolved_config,
        "metrics": metrics, "prediction_hash": prediction_hash,
        "checkpoint_hash": checkpoint_hash, "prediction_path": prediction_path,
        "checkpoint_path": checkpoint_path, "history_path": history_path,
        "runner_metrics_path": runner_metrics_path, "batches_seen": batches_seen,
        "best_epoch": best_epoch, "coverage": coverage,
        "dev_max_date": preflight["max_date"],
    }


def execute(
    experiment_spec_path: Path, config_path: Path, data_dir: Path,
    output_dir: Path, seed: int, max_batches: int | None, mode: str,
    *, repo_root: Path | None = None,
    approved_inputs: tuple[dict[str, Any], dict[str, Any], str] | None = None,
    expected_data_snapshot: DataSnapshot | None = None,
    synthetic_smoke: bool = False,
) -> dict[str, Any]:
    if mode != "valid-only":
        raise ValidationError("run_experiment only permits valid-only mode")
    if max_batches is not None and max_batches <= 0:
        raise ValidationError("max-batches must be positive")
    repo_root = (repo_root or Path(__file__).resolve().parents[1]).resolve()
    if approved_inputs is None:
        spec, config, variant = _load_approved_inputs(
            experiment_spec_path.resolve(), config_path.resolve(), repo_root
        )
    else:
        spec, config, variant = approved_inputs
    settings = _settings(
        config, seed=seed, max_batches=max_batches, synthetic_smoke=synthetic_smoke
    )
    validate_approved_run_semantics(
        {
            "run_variant": variant,
            "objective": settings["objective"],
            "seed": settings["seed"],
            "mode": mode,
            "max_batches": settings["max_batches"],
            "status": "synthetic_smoke" if synthetic_smoke else "completed",
            "evidence_tier": "synthetic_only" if synthetic_smoke else "formal_valid",
        },
        spec,
        config,
        allow_synthetic_smoke=synthetic_smoke,
    )
    source_snapshot = expected_data_snapshot or _capture_data_snapshot(data_dir)
    with tempfile.TemporaryDirectory(prefix="bob-agent-data-snapshot-") as temp:
        snapshot_dir = Path(temp) / "data"
        execution_snapshot = _materialize_data_snapshot(
            data_dir.resolve(), source_snapshot, snapshot_dir
        )
        return _execute_bound_snapshot(
            spec, config, variant, snapshot_dir, output_dir, seed, max_batches,
            mode, execution_snapshot, synthetic_smoke,
        )


def _execute_with_retry(
    operation: Callable[[], dict[str, Any]], attempts: int,
) -> tuple[dict[str, Any], int]:
    retries = 0
    while True:
        try:
            return operation(), retries
        except TransientInfrastructureError:
            if retries >= attempts:
                raise
            retries += 1


def _prepare_output_dir(requested: Path, run_id: str) -> tuple[Path, str | None]:
    requested = requested.resolve()
    if requested.exists() and any(requested.iterdir()):
        evidence = requested.with_name(f"{requested.name}.failed-{run_id}")
        evidence.mkdir(parents=True, exist_ok=False)
        return evidence, f"requested output directory is not empty: {requested}"
    requested.mkdir(parents=True, exist_ok=True)
    return requested, None


def _recorded_command(args: argparse.Namespace, repo_root: Path) -> str:
    parts = [
        "python", "tools/run_experiment.py", "--experiment-spec",
        _display_path(args.experiment_spec, repo_root, "EXPERIMENT_SPEC"),
        "--config", _display_path(args.config, repo_root, "CONFIG"),
        "--data-dir", "<DEV_DATA_DIR>", "--output-dir", "<OUTPUT_DIR>",
        "--seed", str(args.seed), "--mode", args.mode,
    ]
    if args.max_batches is not None:
        parts.extend(("--max-batches", str(args.max_batches)))
    if args.synthetic_smoke:
        parts.append("--synthetic-smoke")
    return shlex.join(parts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a train/valid-only experiment safely.")
    parser.add_argument("--experiment-spec", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-batches", type=int)
    parser.add_argument(
        "--synthetic-smoke", action="store_true",
        help="run an explicitly bounded synthetic-only smoke; never formal evidence",
    )
    parser.add_argument("--mode", choices=("valid-only",), default="valid-only")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started_at, repo_root = _now(), Path(__file__).resolve().parents[1]
    commit_sha, worktree_clean = _git_state(repo_root)
    raw_spec: Any = None
    try:
        raw_spec = read_json(args.experiment_spec.resolve())
    except ValidationError:
        pass
    experiment_id = (
        str(raw_spec.get("experiment_id"))
        if isinstance(raw_spec, dict) and raw_spec.get("experiment_id")
        else "exp-unresolved"
    )
    run_id = (
        f"run-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}-"
        f"{experiment_id}-{commit_sha[:8]}"
    )
    output_dir, output_error = _prepare_output_dir(args.output_dir, run_id)
    command = _recorded_command(args, repo_root)
    manifest: dict[str, Any] = {
        "schema_version": 1, "contract_type": "run_manifest",
        "experiment_id": experiment_id, "run_id": run_id,
        "commit_sha": commit_sha, "worktree_clean": worktree_clean,
        "started_at_utc": started_at, "finished_at_utc": started_at,
        "executor_role": "B",
        "experiment_spec_path": _display_path(args.experiment_spec, repo_root, "EXPERIMENT_SPEC"),
        "config_path": _display_path(args.config, repo_root, "CONFIG"),
        "experiment_spec_hash": None, "run_variant": None,
        "objective": None, "config_input_hash": None,
        "config_hash": None, "config": {},
        "mode": args.mode, "max_batches": args.max_batches,
        "data": {"dataset": "KuaiRand-Pure", "split": "valid", "hash": None},
        "data_hash": None, "seed": args.seed, "dev_max_date": None,
        "environment": {
            "python": platform.python_version(), "platform": platform.platform(),
            "requirements_sha256": sha256_file(repo_root / "requirements.txt"),
        },
        "protected_hashes": {}, "commands": [command],
        "prediction_hash": None, "checkpoint_hash": None, "artifacts": [],
        "status": "failed", "exit_code": 1, "retry_count": 0,
        "manual_interventions": 0, "test_access": False,
        "evidence_tier": "synthetic_only" if args.synthetic_smoke else "formal_valid",
    }
    log_lines = [f"started_at_utc={started_at}", f"run_id={run_id}", f"command={command}"]
    completion_validated = False
    try:
        if output_error:
            raise ValidationError(output_error)
        if not FULL_SHA.fullmatch(commit_sha) or commit_sha == "0" * 40:
            raise ValidationError("current Git commit must be a complete lowercase SHA")
        if not worktree_clean:
            raise ValidationError("worktree must be clean before training")
        manifest["protected_hashes"] = verify_protected_files()
        _require_repository_input(
            args.experiment_spec, repo_root, "experiments", "experiment spec"
        )
        _require_repository_input(
            args.config, repo_root, "configs", "approved config"
        )
        spec_document, spec_input_hash = _read_json_snapshot(
            args.experiment_spec.resolve()
        )
        config_document, config_input_hash = _read_json_snapshot(args.config.resolve())
        spec, config, variant = _validate_approved_inputs(
            spec_document, config_document, args.experiment_spec.resolve(),
            args.config.resolve(), repo_root,
        )
        approved_against = str(spec["approved_against_commit_sha"])
        if not _git_is_ancestor(repo_root, approved_against, commit_sha):
            raise ValidationError("approved_against_commit_sha is not an ancestor of HEAD")
        manifest["experiment_id"] = str(spec["experiment_id"])
        manifest["experiment_spec_hash"] = spec_input_hash
        manifest["run_variant"] = variant
        manifest["config_input_hash"] = config_input_hash
        preview_settings = _settings(
            config, seed=args.seed, max_batches=args.max_batches,
            synthetic_smoke=args.synthetic_smoke,
        )
        manifest["objective"] = preview_settings["objective"]
        manifest["max_batches"] = preview_settings["max_batches"]
        semantic_preview = {
            **manifest,
            "status": "synthetic_smoke" if args.synthetic_smoke else "completed",
        }
        validate_approved_run_semantics(
            semantic_preview, spec, config,
            allow_synthetic_smoke=args.synthetic_smoke,
        )
        if variant == "baseline" and not _git_is_ancestor(
            repo_root, str(config["approved_against_commit_sha"]), commit_sha
        ):
            raise ValidationError(
                "baseline approved_against_commit_sha is not an ancestor of HEAD"
            )
        resolved_preview = {
            **config,
            "resolved_run": {
                "experiment_id": spec["experiment_id"], "run_variant": variant,
                "seed": args.seed,
                "max_batches": preview_settings["max_batches"],
                "mode": args.mode,
            },
        }
        manifest["config"] = resolved_preview
        manifest["config_hash"] = stable_json_hash(resolved_preview)
        data_snapshot = _capture_data_snapshot(args.data_dir.resolve())
        manifest["data_hash"] = data_snapshot.data_hash
        manifest["data"]["hash"] = manifest["data_hash"]
        manifest["data"]["source_hashes"] = dict(data_snapshot.source_hashes)
        if data_snapshot.manifest_hash is not None:
            manifest["data"]["dataset_manifest_hash"] = data_snapshot.manifest_hash
        write_json(output_dir / "resolved_config.json", resolved_preview)
        attempts = int(spec.get("automatic_repair_attempts", 0))
        if attempts not in {0, 1}:
            raise ValidationError("automatic_repair_attempts must be 0 or 1")
        result, retries = _execute_with_retry(
            lambda: execute(
                args.experiment_spec.resolve(), args.config.resolve(),
                args.data_dir.resolve(), output_dir, args.seed, args.max_batches,
                args.mode, repo_root=repo_root,
                approved_inputs=(spec, config, variant),
                expected_data_snapshot=data_snapshot,
                synthetic_smoke=args.synthetic_smoke,
            ), attempts,
        )
        manifest["retry_count"] = retries
        _, current_spec_hash = _read_json_snapshot(args.experiment_spec.resolve())
        if current_spec_hash != spec_input_hash:
            raise ValidationError("experiment spec changed during execution")
        _, current_config_hash = _read_json_snapshot(args.config.resolve())
        if current_config_hash != config_input_hash:
            raise ValidationError("approved config changed during execution")
        _assert_data_snapshot(
            args.data_dir.resolve(), data_snapshot, "during execution"
        )
        executed_config = result.get("resolved_config")
        if (
            not isinstance(executed_config, dict)
            or stable_json_hash(executed_config) != manifest["config_hash"]
        ):
            raise ValidationError(
                "executed resolved config does not match the preflight-bound config"
            )
        final_commit, final_clean = _git_state(repo_root)
        if final_commit != commit_sha or not final_clean:
            raise ValidationError("Git commit/worktree changed during execution")
        completed_manifest = dict(manifest)
        completed_manifest.update(
            status="synthetic_smoke" if args.synthetic_smoke else "completed",
            exit_code=0, run_variant=result["run_variant"],
            objective=result["objective"], prediction_hash=result["prediction_hash"],
            checkpoint_hash=result["checkpoint_hash"], metrics=result["metrics"],
            batches_seen=result["batches_seen"], best_epoch=result["best_epoch"],
            pair_coverage=result["coverage"], dev_max_date=result["dev_max_date"],
        )
        completed_manifest["artifacts"] = [
            {"path": "valid_predictions.csv", "sha256": result["prediction_hash"]},
            {"path": "checkpoint.npz", "sha256": result["checkpoint_hash"]},
            {
                "path": "resolved_config.json",
                "sha256": sha256_file(output_dir / "resolved_config.json"),
            },
            {"path": "training_history.json", "sha256": sha256_file(result["history_path"])},
            {"path": "runner_metrics.json", "sha256": sha256_file(result["runner_metrics_path"])},
        ]
        validate_artifact_files(
            completed_manifest, output_dir, formal_evidence=not args.synthetic_smoke
        )
        manifest = completed_manifest
        completion_validated = True
        log_lines.extend((
            f"batches_seen={result['batches_seen']}", f"retry_count={retries}",
            f"status={completed_manifest['status']}",
        ))
    except Exception as exc:
        manifest["status"] = "failed"
        manifest["exit_code"] = 1
        manifest["error"] = str(exc)
        log_lines.extend(("status=failed", f"error={exc}", traceback.format_exc()))
    except BaseException as exc:
        manifest["status"] = "failed"
        manifest["exit_code"] = 1
        manifest["error"] = f"{type(exc).__name__}: {exc}"
        log_lines.extend((
            "status=failed", f"error={type(exc).__name__}: {exc}",
            traceback.format_exc(),
        ))
        raise
    finally:
        if not completion_validated:
            manifest["status"] = "failed"
            manifest["exit_code"] = 1
        manifest["finished_at_utc"] = _now()
        (output_dir / "run.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
        write_json(output_dir / "run_manifest.json", manifest)
        write_json(output_dir / "exit_status.json", {
            "status": manifest["status"], "exit_code": manifest["exit_code"],
            "finished_at_utc": manifest["finished_at_utc"],
        })
    if manifest["exit_code"] != 0:
        print("RUN_EXPERIMENT=FAIL", file=sys.stderr)
        print(f"ERROR={manifest.get('error', 'unknown error')}", file=sys.stderr)
        print(f"EVIDENCE_DIR={output_dir}", file=sys.stderr)
        return 1
    if args.synthetic_smoke:
        print(f"SYNTHETIC_ROWS={manifest['metrics'].get('rows', 'unknown')}")
        print("SYNTHETIC_SMOKE=PASS")
    else:
        print(f"VALID_ROWS={manifest['metrics'].get('rows', 'unknown')}")
        print(f"VALID_PRIMARY={manifest['metrics']['primary']:.6f}")
    print(f"RUN_ID={manifest['run_id']}")
    print("RUN_EXPERIMENT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
