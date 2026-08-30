"""Protected evaluation gate around the official KuaiRand evaluator."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import secrets
import stat
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
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


@dataclass(frozen=True)
class DirectoryBinding:
    path: Path
    components: tuple[tuple[Path, tuple[int, int, int]], ...]


@dataclass(frozen=True)
class PublishedEvidence:
    path: Path
    identity: tuple[int, int, int]
    digest: str
    directory: DirectoryBinding


def _bind_output_directory(output: Path) -> DirectoryBinding:
    """Bind an existing, no-symlink directory chain for exclusive publication."""

    output = output.absolute()
    output.parent.mkdir(parents=True, exist_ok=True)
    parts = output.parent.parts
    current = Path(parts[0])
    try:
        root_metadata = os.lstat(current)
    except OSError as error:
        raise SecurityError(f"Output directory root is unavailable: {error}") from error
    if stat.S_ISLNK(root_metadata.st_mode) or not stat.S_ISDIR(root_metadata.st_mode):
        raise SecurityError("Output directory root must be an ordinary directory")
    components: list[tuple[Path, tuple[int, int, int]]] = [
        (current, _file_identity(root_metadata))
    ]
    for part in parts[1:]:
        current = current / part
        try:
            metadata = os.lstat(current)
        except OSError as error:
            raise SecurityError(f"Output directory is unavailable: {error}") from error
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise SecurityError("Output directory chain must contain ordinary directories")
        components.append((current, _file_identity(metadata)))
    binding = DirectoryBinding(output.parent, tuple(components))
    _assert_output_directory(binding)
    try:
        os.lstat(output)
    except FileNotFoundError:
        return binding
    except OSError as error:
        raise SecurityError(f"Cannot inspect output destination: {error}") from error
    raise SecurityError("Output destination already exists; overwrite denied")


def _assert_output_directory(binding: DirectoryBinding) -> None:
    for path, identity in binding.components:
        try:
            metadata = os.lstat(path)
        except OSError as error:
            raise SecurityError(f"Output directory binding changed: {error}") from error
        if (
            stat.S_ISLNK(metadata.st_mode)
            or not stat.S_ISDIR(metadata.st_mode)
            or _file_identity(metadata) != identity
        ):
            raise SecurityError("Output directory binding changed during evaluation")


def _fsync_directory(path: Path) -> None:
    """Persist a directory entry where the platform exposes directory fsync."""

    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _verify_published_evidence(binding: PublishedEvidence) -> None:
    _assert_output_directory(binding.directory)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(binding.path, flags)
    except OSError as error:
        raise SecurityError(f"Published evidence is unavailable: {error}") from error
    with os.fdopen(descriptor, "rb") as handle:
        opened = os.fstat(handle.fileno())
        path_metadata = os.lstat(binding.path)
        if (
            stat.S_ISLNK(path_metadata.st_mode)
            or not stat.S_ISREG(opened.st_mode)
            or _file_identity(opened) != binding.identity
            or _file_identity(path_metadata) != binding.identity
        ):
            raise SecurityError("Published evidence path identity changed")
        if _hash_open_file(handle) != binding.digest:
            raise SecurityError("Published evidence hash changed")


def _remove_published_evidence(binding: PublishedEvidence) -> None:
    """Remove only the exact inode created by this invocation."""

    try:
        metadata = os.lstat(binding.path)
        if not stat.S_ISLNK(metadata.st_mode) and _file_identity(metadata) == binding.identity:
            os.unlink(binding.path)
            _fsync_directory(binding.path.parent)
    except OSError:
        pass


def _publish_evidence_exclusively(
    output: Path, payload: bytes, directory: DirectoryBinding,
) -> PublishedEvidence:
    """Write, fsync, and atomically publish evidence without replacing any path."""

    output = output.absolute()
    temp_path = output.parent / f".{output.name}.{secrets.token_hex(16)}.tmp"
    flags = (
        os.O_WRONLY | os.O_CREAT | os.O_EXCL
        | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor = os.open(temp_path, flags, 0o600)
    temp_identity: tuple[int, int, int] | None = None
    publication_complete = False
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode):
                raise SecurityError("Temporary evidence is not an ordinary file")
            temp_identity = _file_identity(opened)
            bound_temp = os.lstat(temp_path)
            if (
                stat.S_ISLNK(bound_temp.st_mode)
                or _file_identity(bound_temp) != temp_identity
            ):
                raise SecurityError("Temporary evidence path changed while writing")

        _assert_output_directory(directory)
        try:
            os.lstat(output)
        except FileNotFoundError:
            pass
        else:
            raise SecurityError("Output destination appeared before publication")
        os.link(temp_path, output, follow_symlinks=False)
        published_metadata = os.lstat(output)
        if (
            stat.S_ISLNK(published_metadata.st_mode)
            or temp_identity is None
            or _file_identity(published_metadata) != temp_identity
        ):
            raise SecurityError("Published evidence is not bound to the fsynced temporary file")
        digest = hashlib.sha256(payload).hexdigest()
        published = PublishedEvidence(output, temp_identity, digest, directory)
        _verify_published_evidence(published)
        _fsync_directory(output.parent)
        publication_complete = True
        return published
    finally:
        if not publication_complete and temp_identity is not None:
            try:
                output_metadata = os.lstat(output)
                if (
                    not stat.S_ISLNK(output_metadata.st_mode)
                    and _file_identity(output_metadata) == temp_identity
                ):
                    os.unlink(output)
                    _fsync_directory(output.parent)
            except OSError:
                pass
        try:
            metadata = os.lstat(temp_path)
            if temp_identity is None or _file_identity(metadata) == temp_identity:
                os.unlink(temp_path)
        except OSError:
            pass


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

    published: PublishedEvidence | None = None
    try:
        protected_hashes = verify_protected_files()
        evaluation_commit = git_head()
        if git_is_dirty():
            raise SecurityError("Worktree is dirty; evaluation denied")
        if os.path.normcase(os.path.abspath(args.output)) == os.path.normcase(
            os.path.abspath(args.prediction)
        ):
            raise SecurityError("Output path must not overwrite the immutable prediction")
        output_directory = _bind_output_directory(args.output)
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
            payload = (
                json.dumps(output, indent=2, ensure_ascii=False) + "\n"
            ).encode("utf-8")
            published = _publish_evidence_exclusively(
                args.output, payload, output_directory
            )
            _verify_published_evidence(published)

        _verify_published_evidence(published)
        if git_head() != evaluation_commit or git_is_dirty():
            raise SecurityError("Git commit or worktree changed during evaluation")
        _verify_published_evidence(published)
    except (OSError, SecurityError, PredictionContractError, ValueError) as error:
        if published is not None:
            _remove_published_evidence(published)
        print(f"EVALUATION DENIED: {error}")
        return 1
    except BaseException:
        if published is not None:
            _remove_published_evidence(published)
        raise

    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
