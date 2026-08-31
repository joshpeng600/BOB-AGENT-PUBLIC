"""Freeze one hidden-test submission without reading labels or scoring it."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import stat
import sys
from pathlib import Path
from typing import BinaryIO, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.final_approval import verify_final_approval
from tools.project_security import SecurityError, git_head, sha256_file
from tools.safe_evaluate import immutable_prediction_snapshot


IDENTITY_HEADER = ["row_id", "user_id", "video_id"]
SUBMISSION_HEADER = ["row_id", "user_id", "video_id", "score"]


def _ordinary_file(path: Path, label: str) -> os.stat_result:
    try:
        metadata = os.lstat(path)
    except OSError as exc:
        raise SecurityError(f"{label} is unavailable: {exc}") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise SecurityError(f"{label} must be an ordinary file, not a symlink")
    return metadata


def _hash_handle(handle: BinaryIO) -> str:
    digest = hashlib.sha256()
    handle.seek(0)
    for block in iter(lambda: handle.read(1024 * 1024), b""):
        digest.update(block)
    handle.seek(0)
    return digest.hexdigest()


def load_hidden_identities(path: Path) -> list[tuple[str, str, str]]:
    """Load identity-only rows; label-bearing inputs are structurally denied."""

    _ordinary_file(path, "hidden-test identity file")
    rows: list[tuple[str, str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        if header != IDENTITY_HEADER:
            raise SecurityError(
                "hidden-test identity header must be exactly "
                "row_id,user_id,video_id; label columns are forbidden"
            )
        for line_number, row in enumerate(reader, 2):
            if len(row) != 3:
                raise SecurityError(f"identity line {line_number} must have 3 fields")
            if row[0] != str(line_number - 2):
                raise SecurityError(
                    f"identity line {line_number} has non-canonical row_id"
                )
            rows.append((row[0], row[1], row[2]))
    if not rows:
        raise SecurityError("hidden-test identity file is empty")
    return rows


def validate_submission_candidate(
    path: Path, identities: Iterable[tuple[str, str, str]]
) -> int:
    _ordinary_file(path, "submission candidate")
    expected = list(identities)
    count = 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        if next(reader, None) != SUBMISSION_HEADER:
            raise SecurityError(
                "submission header must be exactly row_id,user_id,video_id,score"
            )
        for line_number, row in enumerate(reader, 2):
            if len(row) != 4:
                raise SecurityError(f"submission line {line_number} must have 4 fields")
            index = line_number - 2
            if index >= len(expected):
                raise SecurityError("submission contains more rows than identities")
            if tuple(row[:3]) != expected[index]:
                raise SecurityError(
                    f"submission identity mismatch at row_id {expected[index][0]}"
                )
            try:
                score = float(row[3])
            except ValueError as exc:
                raise SecurityError(
                    f"submission score is not numeric at row_id {row[0]}"
                ) from exc
            if not math.isfinite(score):
                raise SecurityError(f"submission score is NaN/Inf at row_id {row[0]}")
            count += 1
    if count != len(expected):
        raise SecurityError(
            f"submission row count {count} does not match identities {len(expected)}"
        )
    return count


def _exclusive_copy(source: Path, output: Path) -> str:
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with source.open("rb") as source_handle, output.open("xb") as output_handle:
            source_hash = _hash_handle(source_handle)
            for block in iter(lambda: source_handle.read(1024 * 1024), b""):
                output_handle.write(block)
            output_handle.flush()
            os.fsync(output_handle.fileno())
    except FileExistsError as exc:
        raise SecurityError("final submission already exists; overwrite denied") from exc
    if sha256_file(output) != source_hash:
        try:
            output.unlink()
        except OSError:
            pass
        raise SecurityError("frozen submission hash does not match candidate bytes")
    return source_hash


def freeze_final_submission(
    *,
    candidate: Path,
    identities_path: Path,
    output: Path,
    manifest_path: Path,
    approval: dict[str, object],
) -> dict[str, object]:
    if output.resolve() == manifest_path.resolve():
        raise SecurityError("submission and manifest paths must differ")
    if manifest_path.exists():
        raise SecurityError("final submission manifest already exists; overwrite denied")
    with immutable_prediction_snapshot(identities_path) as (
        identities_snapshot,
        identity_hash,
    ):
        identities = load_hidden_identities(identities_snapshot)
        with immutable_prediction_snapshot(candidate) as (
            candidate_snapshot,
            candidate_hash,
        ):
            rows = validate_submission_candidate(candidate_snapshot, identities)
            submission_hash = _exclusive_copy(candidate_snapshot, output)
            if submission_hash != candidate_hash:
                raise SecurityError("frozen submission does not match candidate hash")
            manifest = {
                "schema_version": 1,
                "experiment_id": approval["experiment_id"],
                "commit_sha": git_head(),
                "submission_path": str(output.resolve()),
                "submission_sha256": submission_hash,
                "identity_sha256": identity_hash,
                "rows": rows,
                "hidden_test_labels_read": False,
                "local_test_metrics_produced": False,
                "organizer_side_scoring_required": True,
                "submission_overwrite_allowed": False,
                "test_access": False,
            }
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with manifest_path.open("x", encoding="utf-8", newline="\n") as handle:
                    json.dump(manifest, handle, indent=2, sort_keys=True)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
            except OSError as exc:
                try:
                    output.unlink()
                except OSError:
                    pass
                raise SecurityError(
                    f"final submission manifest could not be published: {exc}"
                ) from exc
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approval", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--identities", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()
    try:
        approval = verify_final_approval(args.approval)
        manifest = freeze_final_submission(
            candidate=args.candidate,
            identities_path=args.identities,
            output=args.output,
            manifest_path=args.manifest,
            approval=approval,
        )
    except (SecurityError, OSError, ValueError) as exc:
        print(f"FINAL_SUBMISSION=DENIED\nERROR={exc}\ntest_access=false")
        return 1
    print("FINAL_SUBMISSION=FROZEN")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
