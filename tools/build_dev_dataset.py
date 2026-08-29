from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.common import VALID_END, ValidationError, sha256_file, write_json


def _copy_log(source: Path, destination: Path, max_date: int) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    dates: list[int] = []
    with source.open("r", encoding="utf-8-sig", newline="") as src:
        reader = csv.DictReader(src)
        if reader.fieldnames is None or "date" not in reader.fieldnames:
            raise ValidationError(f"log must have a date column: {source}")
        with destination.open("w", encoding="utf-8", newline="") as dst:
            writer = csv.DictWriter(dst, fieldnames=reader.fieldnames, lineterminator="\n")
            writer.writeheader()
            for line_number, row in enumerate(reader, start=2):
                try:
                    date = int(row.get("date", ""))
                except ValueError as exc:
                    raise ValidationError(f"{source}:{line_number}: invalid date") from exc
                if date <= max_date:
                    writer.writerow(row)
                    count += 1
                    dates.append(date)
    return {
        "kind": "log",
        "rows": count,
        "min_date": min(dates) if dates else None,
        "max_date": max(dates) if dates else None,
        "sha256": sha256_file(destination),
    }


def build(source: Path, output: Path, max_date: int) -> dict[str, Any]:
    source = source.resolve()
    output = output.resolve()
    if not source.is_dir():
        raise ValidationError(f"source is not a directory: {source}")
    if max_date > VALID_END:
        raise ValidationError(f"max-date {max_date} crosses the experiment cutoff {VALID_END}")
    if source == output or source in output.parents:
        raise ValidationError("output must not be the source directory or a child of it")
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValidationError("output directory must be empty to prevent stale or mixed-split files")

    log_files = sorted(path for path in source.glob("log*.csv") if path.is_file())
    if not log_files:
        raise ValidationError("source contains no log*.csv files")
    missing_logs = [name for name in (
        "log_standard_4_08_to_4_21_pure.csv",
        "log_standard_4_22_to_5_08_pure.csv",
    ) if not (source / name).is_file()]
    if missing_logs:
        raise ValidationError(f"missing required logs: {', '.join(missing_logs)}")
    static_files = sorted(
        path for path in source.glob("*.csv")
        if path.is_file()
        and not path.name.lower().startswith("log")
        and "feature" in path.name.lower()
    )
    if not any(path.name == "video_features_basic_pure.csv" for path in static_files):
        raise ValidationError("missing required static table: video_features_basic_pure.csv")

    files: dict[str, Any] = {}
    for path in static_files:
        destination = output / path.name
        shutil.copy2(path, destination)
        files[path.name] = {
            "kind": "static",
            "rows": _count_data_rows(destination),
            "min_date": None,
            "max_date": None,
            "sha256": sha256_file(destination),
        }
    for path in log_files:
        destination = output / path.name
        files[path.name] = _copy_log(path, destination, max_date)

    observed_dates = [
        date
        for item in files.values()
        if item["kind"] == "log"
        for date in (item["min_date"], item["max_date"])
        if date is not None
    ]
    manifest = {
        "format_version": 1,
        "max_date_requested": max_date,
        "rows": sum(item["rows"] for item in files.values() if item["kind"] == "log"),
        "min_date": min(observed_dates) if observed_dates else None,
        "max_date": max(observed_dates) if observed_dates else None,
        "test_rows": 0,
        "files": files,
    }
    write_json(output / "dataset_manifest.json", manifest)
    return manifest


def _count_data_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return max(sum(1 for _ in csv.reader(handle)) - 1, 0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a train/valid-only development dataset.")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-date", type=int, default=VALID_END)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest = build(args.source, args.output, args.max_date)
    except (OSError, ValidationError) as exc:
        print(f"BUILD_DEV_DATASET=FAIL\nERROR={exc}", file=sys.stderr)
        return 1
    print(f"ROWS={manifest['rows']}")
    print(f"MIN_DATE={manifest['min_date']}")
    print(f"MAX_DATE={manifest['max_date']}")
    print("TEST_ROWS=0")
    print("BUILD_DEV_DATASET=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
