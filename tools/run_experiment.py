from __future__ import annotations

import argparse
import csv
import importlib
import math
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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


def ensure_aligned_lengths(*arrays: Sequence[Any]) -> int:
    lengths = [len(array) for array in arrays]
    if not lengths or len(set(lengths)) != 1:
        raise ValidationError(f"array length mismatch: {lengths}")
    return lengths[0]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git_state(repo_root: Path) -> tuple[str, bool]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        dirty = bool(subprocess.run(
            ["git", "status", "--porcelain"], cwd=repo_root, check=True,
            capture_output=True, text=True,
        ).stdout.strip())
        return commit, dirty
    except (OSError, subprocess.CalledProcessError):
        return "0" * 40, True


def _data_hash(data_dir: Path) -> str:
    manifest = data_dir / "dataset_manifest.json"
    if manifest.is_file():
        return sha256_file(manifest)
    files = []
    for name in (*OFFICIAL_LOG_FILES, *REQUIRED_STATIC_FILES):
        path = data_dir / name
        files.append({"path": name, "sha256": sha256_file(path)})
    return stable_json_hash(files)


def _settings(config: dict[str, Any]) -> dict[str, Any]:
    model = config.get("model", "FM")
    model_config = model if isinstance(model, dict) else {}
    training = config.get("training", {})
    if not isinstance(training, dict):
        raise ValidationError("training config must be an object")

    def value(name: str, default: Any) -> Any:
        if name in training:
            return training[name]
        if name in model_config:
            return model_config[name]
        return config.get(name, default)

    name = model_config.get("name", "FM") if isinstance(model, dict) else model
    settings = {
        "model_name": str(name),
        "model_factory": value("factory", None),
        "k": int(value("k", 16)),
        "lr": float(value("lr", 0.001)),
        "l2": float(value("l2", 1e-6)),
        "batch": int(value("batch", 8192)),
        "max_epochs": int(value("max_epochs", 40)),
        "patience": int(value("patience", 4)),
        "min_delta": float(value("early_stopping_min_delta", 1e-5)),
    }
    if settings["batch"] <= 0 or settings["max_epochs"] <= 0 or settings["patience"] <= 0:
        raise ValidationError("batch, max_epochs, and patience must be positive")
    if settings["model_name"].lower() != "fm" and not settings["model_factory"]:
        raise ValidationError("non-FM models must provide model.factory='module:function'")
    return settings


def _load_factory(spec: str):
    if ":" not in spec:
        raise ValidationError("model factory must use module:function syntax")
    module_name, function_name = spec.split(":", 1)
    try:
        function = getattr(importlib.import_module(module_name), function_name)
    except (ImportError, AttributeError) as exc:
        raise ValidationError(f"cannot import model factory {spec}: {exc}") from exc
    if not callable(function):
        raise ValidationError(f"model factory is not callable: {spec}")
    return function


def _build_model(
    settings: dict[str, Any],
    field_dim: int,
    config: dict[str, Any],
    seed: int,
    starter_data: Any,
    starter_evaluate: Any,
):
    if settings["model_factory"]:
        return _load_factory(settings["model_factory"])(field_dim=field_dim, config=config, seed=seed)
    sentinel = object()
    previous_data = sys.modules.get("data", sentinel)
    previous_evaluate = sys.modules.get("evaluate", sentinel)
    try:
        # The preserved official file uses flat imports because it is normally run as a script.
        # Temporarily map those names without editing anything under starter/.
        sys.modules["data"] = starter_data
        sys.modules["evaluate"] = starter_evaluate
        baseline = importlib.import_module("starter.baseline")
    except ImportError as exc:
        raise ValidationError(
            "starter.baseline is unavailable; merge the official Starter Kit before running experiments"
        ) from exc
    finally:
        if previous_data is sentinel:
            sys.modules.pop("data", None)
        else:
            sys.modules["data"] = previous_data
        if previous_evaluate is sentinel:
            sys.modules.pop("evaluate", None)
        else:
            sys.modules["evaluate"] = previous_evaluate
    try:
        return baseline.FM(
            field_dim,
            k=settings["k"],
            lr=settings["lr"],
            l2=settings["l2"],
            seed=seed,
        )
    except AttributeError as exc:
        raise ValidationError("starter.baseline must expose FM") from exc


def _save_checkpoint(model: Any, path: Path) -> str:
    try:
        import numpy as np
    except ImportError as exc:
        raise ValidationError("numpy is required to save the FM checkpoint") from exc
    state = {name: getattr(model, name) for name in ("V", "W", "b") if hasattr(model, name)}
    if not state:
        raise ValidationError("model exposes no checkpoint state (expected V/W/b)")
    np.savez(path, **state)
    return sha256_file(path)


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
    normalized: dict[str, Any] = {}
    for key, value in metrics.items():
        if isinstance(value, bool):
            normalized[key] = value
        elif isinstance(value, int):
            normalized[key] = value
        elif hasattr(value, "item"):
            normalized[key] = value.item()
        else:
            normalized[key] = value
    return normalized


def execute(
    config_path: Path,
    data_dir: Path,
    output_dir: Path,
    seed: int,
    max_batches: int | None,
    mode: str,
) -> dict[str, Any]:
    if mode not in {"experiment", "valid-only"}:
        raise ValidationError("run_experiment only permits experiment/valid-only modes")
    if max_batches is not None and max_batches <= 0:
        raise ValidationError("max-batches must be positive")
    config = read_json(config_path)
    if not isinstance(config, dict):
        raise ValidationError("config root must be an object")
    inspect_data(data_dir, "experiment", config)
    settings = _settings(config)

    try:
        starter_data = importlib.import_module("starter.data")
        starter_evaluate = importlib.import_module("starter.evaluate")
    except ImportError as exc:
        raise ValidationError(
            "starter.data/evaluate are unavailable; merge the official Starter Kit before running experiments"
        ) from exc

    splits = starter_data.load(str(data_dir))
    if not isinstance(splits, dict) or "train" not in splits or "valid" not in splits:
        raise ValidationError("starter.data.load must return train and valid splits")
    if splits.get("test"):
        raise ValidationError("development data unexpectedly produced non-empty held-out rows")
    encoded, field_dim = starter_data.encode(splits)
    X_train, y_train, _ = encoded["train"]
    X_valid, y_valid, users_valid = encoded["valid"]
    ensure_aligned_lengths(X_train, y_train)
    ensure_aligned_lengths(X_valid, y_valid, users_valid, splits["valid"])

    try:
        import numpy as np
    except ImportError as exc:
        raise ValidationError("numpy is required by the official Starter Kit") from exc
    model = _build_model(
        settings, field_dim, config, seed, starter_data, starter_evaluate,
    )
    rng = np.random.default_rng(seed)
    best_primary = float("-inf")
    best_state = None
    bad_epochs = 0
    batches_seen = 0
    history: list[dict[str, Any]] = []
    for epoch in range(settings["max_epochs"]):
        indices = rng.permutation(len(y_train))
        for start in range(0, len(indices), settings["batch"]):
            if max_batches is not None and batches_seen >= max_batches:
                break
            batch_indices = indices[start:start + settings["batch"]]
            model.step(X_train[batch_indices], y_train[batch_indices])
            batches_seen += 1
        scores = model.predict(X_valid)
        ensure_aligned_lengths(scores, y_valid)
        if not np.isfinite(np.asarray(scores, dtype=float)).all():
            raise ValidationError("model produced NaN/Inf validation scores")
        metrics = _json_metrics(starter_evaluate.evaluate(users_valid, y_valid, scores))
        primary = float(metrics["primary"])
        history.append({"epoch": epoch + 1, "batches_seen": batches_seen, "valid": metrics})
        if primary > best_primary + settings["min_delta"]:
            best_primary = primary
            bad_epochs = 0
            if all(hasattr(model, name) for name in ("V", "W", "b")):
                best_state = (model.V.copy(), model.W.copy(), model.b)
        else:
            bad_epochs += 1
        if max_batches is not None and batches_seen >= max_batches:
            break
        if bad_epochs >= settings["patience"]:
            break
    if best_state is not None:
        model.V, model.W, model.b = best_state

    final_scores = model.predict(X_valid)
    ensure_aligned_lengths(final_scores, splits["valid"])
    if not np.isfinite(np.asarray(final_scores, dtype=float)).all():
        raise ValidationError("model produced NaN/Inf final scores")
    metrics = _json_metrics(starter_evaluate.evaluate(users_valid, y_valid, final_scores))
    prediction_path = output_dir / "valid_predictions.csv"
    prediction_hash = _write_predictions(prediction_path, splits["valid"], final_scores)
    checkpoint_path = output_dir / "checkpoint.npz"
    checkpoint_hash = _save_checkpoint(model, checkpoint_path)
    write_json(output_dir / "metrics.json", {"split": "valid", **metrics})
    write_json(output_dir / "training_history.json", history)
    return {
        "metrics": metrics,
        "prediction_hash": prediction_hash,
        "checkpoint_hash": checkpoint_hash,
        "prediction_path": str(prediction_path),
        "checkpoint_path": str(checkpoint_path),
        "batches_seen": batches_seen,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a train/valid-only experiment safely.")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-batches", type=int)
    parser.add_argument("--mode", choices=("experiment", "valid-only"), default="valid-only")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    started_at = _now()
    repo_root = Path(__file__).resolve().parents[1]
    commit, dirty = _git_state(repo_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    recorded_command = [
        "python", "tools/run_experiment.py",
        "--config", args.config.name,
        "--data-dir", "<DATA_DIR>",
        "--output-dir", "<OUTPUT_DIR>",
        "--seed", str(args.seed),
        "--mode", args.mode,
    ]
    if args.max_batches is not None:
        recorded_command.extend(("--max-batches", str(args.max_batches)))
    manifest: dict[str, Any] = {
        "exp_id": args.config.stem,
        "commit": commit,
        "dirty": dirty,
        "config_hash": "not-read",
        "data_hash": "not-read",
        "seed": args.seed,
        "started_at": started_at,
        "ended_at": started_at,
        "exit_code": 1,
        "checkpoint_hash": "not-produced",
        "prediction_hash": "not-produced",
        "log_path": "run.log",
        "manual_intervention": False,
        "command": recorded_command,
        "mode": args.mode,
        "split": "valid",
        "test_access": False,
    }
    log_lines: list[str] = [f"started_at={started_at}", f"mode={args.mode}", f"seed={args.seed}"]
    try:
        config = read_json(args.config.resolve())
        resolved = {**config, "seed": args.seed, "max_batches": args.max_batches, "mode": args.mode}
        write_json(output_dir / "resolved_config.json", resolved)
        manifest["exp_id"] = str(config.get("exp_id", args.config.stem))
        manifest["config_hash"] = stable_json_hash(resolved)
        manifest["data_hash"] = _data_hash(args.data_dir.resolve())
        result = execute(
            args.config.resolve(), args.data_dir.resolve(), output_dir,
            args.seed, args.max_batches, args.mode,
        )
        manifest.update(
            exit_code=0,
            checkpoint_hash=result["checkpoint_hash"],
            prediction_hash=result["prediction_hash"],
            metrics=result["metrics"],
            batches_seen=result["batches_seen"],
        )
        log_lines.append(f"batches_seen={result['batches_seen']}")
        log_lines.append("status=PASS")
    except Exception as exc:  # manifest and exit status must survive every run failure
        manifest["error"] = str(exc)
        log_lines.extend((f"status=FAIL", f"error={exc}", traceback.format_exc()))
    finally:
        manifest["ended_at"] = _now()
        (output_dir / "run.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
        write_json(output_dir / "run_manifest.json", manifest)
        write_json(
            output_dir / "exit_status.json",
            {"exit_code": manifest["exit_code"], "ended_at": manifest["ended_at"]},
        )
    if manifest["exit_code"] != 0:
        print("RUN_EXPERIMENT=FAIL", file=sys.stderr)
        print(f"ERROR={manifest.get('error', 'unknown error')}", file=sys.stderr)
        return 1
    print(f"VALID_ROWS={manifest['metrics'].get('rows', 'unknown')}")
    print(f"VALID_PRIMARY={manifest['metrics']['primary']:.6f}")
    print("RUN_EXPERIMENT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
