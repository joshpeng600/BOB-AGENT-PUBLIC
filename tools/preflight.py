from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.common import (
    OFFICIAL_LOG_FILES,
    REQUIRED_LOG_COLUMNS,
    REQUIRED_STATIC_FILES,
    TEST_START,
    TRAIN_START,
    VALID_END,
    ValidationError,
    read_json,
)


def _require_columns(path: Path, fieldnames: list[str] | None, required: tuple[str, ...]) -> None:
    if fieldnames is None:
        raise ValidationError(f"CSV has no header: {path}")
    missing = [name for name in required if name not in fieldnames]
    if missing:
        raise ValidationError(f"{path}: missing columns: {', '.join(missing)}")


def _check_config(config: Any, mode: str) -> None:
    if config is None:
        return
    if not isinstance(config, dict):
        raise ValidationError("config root must be a JSON object")

    risky_true_keys = {
        "score_test",
        "test_scoring",
        "evaluate_test",
        "use_test",
        "load_test_labels",
    }
    split_keys = {"split", "evaluation_split", "eval_split", "score_split"}
    split_list_keys = {"splits", "evaluation_splits", "eval_splits", "score_splits"}

    def walk(value: Any, path: str = "config") -> None:
        if isinstance(value, dict):
            for raw_key, child in value.items():
                key = str(raw_key).lower()
                child_path = f"{path}.{raw_key}"
                if mode == "experiment" and key in risky_true_keys and child is True:
                    raise ValidationError(f"test scoring request denied at {child_path}")
                if mode == "experiment" and key in split_keys and str(child).lower() == "test":
                    raise ValidationError(f"test split request denied at {child_path}")
                if mode == "experiment" and key in split_list_keys:
                    values = child if isinstance(child, list) else [child]
                    if any(str(item).lower() == "test" for item in values):
                        raise ValidationError(f"test split request denied at {child_path}")
                walk(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")

    walk(config)


def inspect_data(data_dir: Path, mode: str = "experiment", config: Any = None) -> dict[str, Any]:
    data_dir = data_dir.resolve()
    if not data_dir.is_dir():
        raise ValidationError(f"data directory does not exist: {data_dir}")
    if mode not in {"experiment", "final"}:
        raise ValidationError(f"unsupported mode: {mode}")
    _check_config(config, mode)

    for name in (*OFFICIAL_LOG_FILES, *REQUIRED_STATIC_FILES):
        if not (data_dir / name).is_file():
            raise ValidationError(f"missing required file: {name}")

    labels: set[int] = set()
    dates: list[int] = []
    rows = 0
    test_rows = 0
    split_rows = {"train": 0, "valid": 0, "test": 0}
    for name in OFFICIAL_LOG_FILES:
        path = data_dir / name
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            _require_columns(path, reader.fieldnames, REQUIRED_LOG_COLUMNS)
            for line_number, row in enumerate(reader, start=2):
                for column in REQUIRED_LOG_COLUMNS:
                    if row.get(column) is None or row[column].strip() == "":
                        raise ValidationError(f"{path}:{line_number}: null/empty {column}")
                try:
                    date = int(row["date"])
                except ValueError as exc:
                    raise ValidationError(f"{path}:{line_number}: invalid date {row['date']!r}") from exc
                if date < TRAIN_START or date > 99999999:
                    raise ValidationError(f"{path}:{line_number}: date outside supported range: {date}")
                try:
                    label = int(row["long_view"])
                except ValueError as exc:
                    raise ValidationError(
                        f"{path}:{line_number}: long_view must be 0 or 1"
                    ) from exc
                if label not in {0, 1} or row["long_view"].strip() not in {"0", "1"}:
                    raise ValidationError(f"{path}:{line_number}: long_view must be exactly 0 or 1")
                try:
                    float(row["duration_ms"])
                except ValueError as exc:
                    raise ValidationError(f"{path}:{line_number}: invalid duration_ms") from exc
                labels.add(label)
                dates.append(date)
                rows += 1
                if date <= 20220421:
                    split_rows["train"] += 1
                elif date <= VALID_END:
                    split_rows["valid"] += 1
                elif date >= TEST_START:
                    split_rows["test"] += 1
                    test_rows += 1

    if not rows:
        raise ValidationError("logs contain no rows")
    if max(dates) > 20220508:
        raise ValidationError(f"data contains date after official range: {max(dates)}")
    if labels != {0, 1}:
        raise ValidationError(f"label values must include both 0 and 1, observed {sorted(labels)}")
    if split_rows["train"] == 0 or split_rows["valid"] == 0:
        raise ValidationError("experiment data must contain both train and valid rows")
    if mode == "experiment" and max(dates) > VALID_END:
        raise ValidationError(
            f"experiment data contains date {max(dates)} after cutoff {VALID_END}"
        )

    video_path = data_dir / "video_features_basic_pure.csv"
    with video_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        _require_columns(video_path, reader.fieldnames, ("video_id", "author_id"))
        static_rows = 0
        for line_number, row in enumerate(reader, start=2):
            if not row.get("video_id", "").strip() or not row.get("author_id", "").strip():
                raise ValidationError(f"{video_path}:{line_number}: empty video_id/author_id")
            static_rows += 1
    if static_rows == 0:
        raise ValidationError("video feature table contains no rows")

    return {
        "rows": rows,
        "test_rows": test_rows,
        "min_date": min(dates),
        "max_date": max(dates),
        "label_values": sorted(labels),
        "split_rows": split_rows,
        "final_approval_required": mode == "final",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate data and configuration before execution.")
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--mode", choices=("experiment", "final"), required=True)
    parser.add_argument("--config", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = read_json(args.config) if args.config else None
        result = inspect_data(args.data_dir, args.mode, config)
    except (OSError, ValidationError) as exc:
        print("PREFLIGHT=FAIL", file=sys.stderr)
        print(f"ERROR={exc}", file=sys.stderr)
        return 1
    print(f"ROWS={result['rows']}")
    print(f"TEST_ROWS={result['test_rows']}")
    print(f"MIN_DATE={result['min_date']}")
    print(f"MAX_DATE={result['max_date']}")
    print(f"LABEL_VALUES={result['label_values']}")
    if result["final_approval_required"]:
        print("FINAL_APPROVAL_REQUIRED=1")
    print("PREFLIGHT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
