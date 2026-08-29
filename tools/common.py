from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


TRAIN_START = 20220408
TRAIN_END = 20220421
VALID_START = 20220422
VALID_END = 20220428
TEST_START = 20220429
TEST_END = 20220508

OFFICIAL_LOG_FILES = (
    "log_standard_4_08_to_4_21_pure.csv",
    "log_standard_4_22_to_5_08_pure.csv",
)
REQUIRED_STATIC_FILES = ("video_features_basic_pure.csv",)
REQUIRED_LOG_COLUMNS = (
    "date",
    "user_id",
    "video_id",
    "tab",
    "duration_ms",
    "long_view",
)


class ValidationError(ValueError):
    """Raised when an input violates a Track 2 safety contract."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_json_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise ValidationError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON in {path}: {exc}") from exc


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def official_log_paths(data_dir: Path) -> list[Path]:
    return [data_dir / name for name in OFFICIAL_LOG_FILES]


def iter_csv_rows(path: Path) -> Iterable[tuple[int, dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValidationError(f"CSV has no header: {path}")
        for line_number, row in enumerate(reader, start=2):
            yield line_number, row


def split_bounds(split: str) -> tuple[int, int]:
    bounds = {
        "train": (TRAIN_START, TRAIN_END),
        "valid": (VALID_START, VALID_END),
        "test": (TEST_START, TEST_END),
    }
    try:
        return bounds[split]
    except KeyError as exc:
        raise ValidationError(f"unknown split: {split}") from exc


def load_split_identity_rows(data_dir: Path, split: str) -> list[tuple[str, str]]:
    lo, hi = split_bounds(split)
    rows: list[tuple[str, str]] = []
    for path in official_log_paths(data_dir):
        if not path.is_file():
            raise ValidationError(f"missing required log: {path}")
        for line_number, row in iter_csv_rows(path):
            try:
                date = int(row.get("date", ""))
            except ValueError as exc:
                raise ValidationError(f"{path}:{line_number}: invalid date") from exc
            if lo <= date <= hi:
                rows.append((row.get("user_id", ""), row.get("video_id", "")))
    return rows
