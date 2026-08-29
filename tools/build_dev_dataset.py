"""Build a small deterministic development copy from train and validation only."""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.contracts import DEV_MAX_DATE, LOG_FILES


def build_dev_dataset(data_dir: str | Path, output_dir: str | Path, rows_per_log: int = 1000) -> dict[str, int]:
    if rows_per_log < 1:
        raise ValueError("rows_per_log must be at least 1")
    source, destination = Path(data_dir), Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    copied: dict[str, int] = {}
    for filename in LOG_FILES:
        count = 0
        with (source / filename).open(newline="") as reader, (destination / filename).open("w", newline="") as writer:
            rows = csv.DictReader(reader)
            if rows.fieldnames is None:
                raise ValueError(f"{filename}: missing header")
            out = csv.DictWriter(writer, fieldnames=rows.fieldnames)
            out.writeheader()
            for row in rows:
                if int(row["date"]) > DEV_MAX_DATE:
                    continue
                out.writerow(row)  # preserves original file order
                count += 1
                if count >= rows_per_log:
                    break
        copied[filename] = count
    return copied


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--rows-per-log", type=int, default=1000)
    args = parser.parse_args()
    print(build_dev_dataset(args.data_dir, args.output_dir, args.rows_per_log))
