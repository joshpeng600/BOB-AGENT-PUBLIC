"""Protected evaluation gate around the official KuaiRand evaluator."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import stat
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from starter import evaluate as official_evaluator
from tools.final_approval import verify_final_approval
from tools.official_rows import load_splits
from tools.prediction_contract import (
    PredictionContractError,
    validate_evaluator_arrays,
    validate_prediction_file,
)
from tools.project_security import (
    SecurityError,
    git_head,
    git_is_dirty,
    sha256_file,
    verify_protected_files,
)


def _file_signature(metadata: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        int(metadata.st_dev),
        int(metadata.st_ino),
        int(metadata.st_mode),
        int(metadata.st_size),
        int(metadata.st_mtime_ns),
        int(metadata.st_ctime_ns),
    )


def _file_identity(metadata: os.stat_result) -> tuple[int, int, int]:
    return (int(metadata.st_dev), int(metadata.st_ino), int(metadata.st_mode))


def _hash_open_file(handle) -> str:
    digest = hashlib.sha256()
    handle.seek(0)
    for block in iter(lambda: handle.read(1024 * 1024), b""):
        digest.update(block)
    return digest.hexdigest()


@contextmanager
def immutable_prediction_snapshot(source: Path) -> Iterator[tuple[Path, str]]:
    """Yield a private snapshot bound to one no-follow source-file handle."""

    source = source.absolute()
    try:
        initial_path = os.lstat(source)
    except OSError as error:
        raise SecurityError(f"Prediction file is unavailable: {error}") from error
    if stat.S_ISLNK(initial_path.st_mode) or not stat.S_ISREG(initial_path.st_mode):
        raise SecurityError("Prediction must be an ordinary file, not a symlink")

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(source, flags)
    except OSError as error:
        raise SecurityError(f"Cannot safely open prediction: {error}") from error

    try:
        with os.fdopen(descriptor, "rb") as source_handle:
            opened = os.fstat(source_handle.fileno())
            bound_path = os.lstat(source)
            if (
                not stat.S_ISREG(opened.st_mode)
                or _file_identity(initial_path) != _file_identity(opened)
                or _file_identity(bound_path) != _file_identity(opened)
            ):
                raise SecurityError("Prediction path changed while opening")
            opened_signature = _file_signature(opened)
            path_signature = _file_signature(bound_path)

            with tempfile.TemporaryDirectory(prefix="track2-e-prediction-") as tmp:
                snapshot = Path(tmp) / "valid_predictions.csv"
                digest = hashlib.sha256()
                source_handle.seek(0)
                with snapshot.open("xb") as destination:
                    for block in iter(lambda: source_handle.read(1024 * 1024), b""):
                        digest.update(block)
                        destination.write(block)
                    destination.flush()
                    os.fsync(destination.fileno())
                prediction_hash = digest.hexdigest()
                after_capture = os.fstat(source_handle.fileno())
                if _file_signature(after_capture) != opened_signature:
                    raise SecurityError("Prediction changed while creating immutable snapshot")
                snapshot.chmod(0o400)

                yield snapshot, prediction_hash

                try:
                    final_path = os.lstat(source)
                    final_handle = os.fstat(source_handle.fileno())
                except OSError as error:
                    raise SecurityError(
                        f"Prediction binding changed during evaluation: {error}"
                    ) from error
                if (
                    _file_signature(final_path) != path_signature
                    or _file_signature(final_handle) != opened_signature
                ):
                    raise SecurityError("Prediction path changed during evaluation")
                if _hash_open_file(source_handle) != prediction_hash:
                    raise SecurityError("Prediction bytes changed during evaluation")
                if sha256_file(snapshot) != prediction_hash:
                    raise SecurityError("Immutable prediction snapshot changed")
    except BaseException:
        # os.fdopen owns and closes descriptor once entered; close only if entry failed.
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prediction", required=True, type=Path)
    parser.add_argument("--split", required=True, choices=["valid", "test"])
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--approval",
        type=Path,
        help="Human approval JSON; required for any test operation",
    )
    args = parser.parse_args()

    try:
        protected_hashes = verify_protected_files()
        evaluation_commit = git_head()
        if git_is_dirty():
            raise SecurityError("Worktree is dirty; evaluation denied")
        if args.output.resolve() == args.prediction.resolve():
            raise SecurityError("Output path must not overwrite the immutable prediction")
        if args.split == "test":
            if args.approval is None:
                raise SecurityError(
                    "Normal mode only permits valid; test requires --approval"
                )
            verify_final_approval(args.approval)

        with immutable_prediction_snapshot(args.prediction) as (
            snapshot_path,
            prediction_hash,
        ):
            splits = load_splits(args.data_dir)
            rows = splits[args.split]
            scores = validate_prediction_file(snapshot_path, rows)
            users, labels, scores = validate_evaluator_arrays(
                [row[1] for row in rows],
                [row[6] for row in rows],
                scores,
            )
            metrics = official_evaluator.evaluate(users, labels, scores)
            expected_primary = (
                float(metrics["GAUC"]) + float(metrics["nDCG@5"])
            ) / 2.0
            if not math.isclose(float(metrics["primary"]), expected_primary):
                raise SecurityError(
                    "Official primary is not the arithmetic mean of GAUC and nDCG@5"
                )
        if git_head() != evaluation_commit or git_is_dirty():
            raise SecurityError("Git commit or worktree changed during evaluation")
    except (OSError, SecurityError, PredictionContractError, ValueError) as error:
        print(f"EVALUATION DENIED: {error}")
        return 1

    output = {
        "GAUC": metrics["GAUC"],
        "nDCG@5": metrics["nDCG@5"],
        "primary": metrics["primary"],
        "rows": metrics["rows"],
        "users": metrics["users"],
        "evaluator_hash": protected_hashes["starter/evaluate.py"],
        "evaluator_role": "E",
        "split": args.split,
        "prediction_hash": prediction_hash,
        "commit_sha": evaluation_commit,
        "worktree_clean": True,
        "test_access": args.split == "test",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
