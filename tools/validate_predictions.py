from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.common import ValidationError, load_split_identity_rows


HEADER = ["row_id", "user_id", "video_id", "score"]


def validate(prediction: Path, data_dir: Path, split: str) -> dict[str, int | str]:
    if split != "valid":
        raise ValidationError("ordinary prediction validation only permits split=valid")
    expected = load_split_identity_rows(data_dir.resolve(), split)
    try:
        handle = prediction.resolve().open("r", encoding="utf-8-sig", newline="")
    except FileNotFoundError as exc:
        raise ValidationError(f"prediction file not found: {prediction}") from exc
    with handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        if header != HEADER:
            raise ValidationError(f"header must be {','.join(HEADER)}, observed {header}")
        count = 0
        for line_number, record in enumerate(reader, start=2):
            if len(record) != 4:
                raise ValidationError(f"line {line_number}: expected 4 fields, observed {len(record)}")
            row_id, user_id, video_id, raw_score = record
            if row_id != str(count):
                raise ValidationError(
                    f"line {line_number}: row_id {row_id!r}, expected contiguous value {count}"
                )
            if count >= len(expected):
                raise ValidationError(f"prediction has more than {len(expected)} expected rows")
            if (user_id, video_id) != expected[count]:
                raise ValidationError(
                    f"line {line_number}: identity {(user_id, video_id)} does not match {expected[count]}"
                )
            try:
                score = float(raw_score)
            except ValueError as exc:
                raise ValidationError(f"line {line_number}: score is not numeric") from exc
            if not math.isfinite(score):
                raise ValidationError(f"line {line_number}: score is NaN/Inf")
            count += 1
    if count != len(expected):
        raise ValidationError(f"prediction has {count} rows; expected {len(expected)}")
    return {"rows": count, "split": split}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate prediction format and row alignment.")
    parser.add_argument("--prediction", required=True, type=Path)
    parser.add_argument("--split", required=True, choices=("valid",))
    parser.add_argument("--data-dir", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = validate(args.prediction, args.data_dir, args.split)
    except (OSError, ValidationError) as exc:
        print("PREDICTIONS=FAIL", file=sys.stderr)
        print(f"ERROR={exc}", file=sys.stderr)
        return 1
    print(f"ROWS={result['rows']}")
    print(f"SPLIT={result['split']}")
    print("PREDICTIONS=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
