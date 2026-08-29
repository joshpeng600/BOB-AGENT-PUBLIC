"""Read-only CSV audit: no fabricated metrics when source data is unavailable."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.manifest import sha256_file, write_manifest


CSV_FILES = (
    "log_standard_4_08_to_4_21_pure.csv",
    "log_standard_4_22_to_5_08_pure.csv",
    "log_random_4_22_to_5_08_pure.csv",
    "user_features_pure.csv",
    "video_features_basic_pure.csv",
    "video_features_statistic_pure.csv",
)


def audit_csv(path: Path) -> dict:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        missing = Counter()
        labels, dates = set(), []
        pair_counts, user_counts, video_counts = Counter(), Counter(), Counter()
        row_count = 0
        for row in reader:
            row_count += 1
            for column in headers:
                if row.get(column, "") == "":
                    missing[column] += 1
            if "date" in row and row["date"]:
                dates.append(int(row["date"]))
            if "long_view" in row:
                labels.add(row["long_view"])
            if "user_id" in row:
                user_counts[row["user_id"]] += 1
            if "video_id" in row:
                video_counts[row["video_id"]] += 1
            if "user_id" in row and "video_id" in row:
                pair_counts[(row["user_id"], row["video_id"])] += 1
    return {
        "file": path.name,
        "sha256": sha256_file(path),
        "headers": headers,
        "row_count": row_count,
        "date_range": [min(dates), max(dates)] if dates else None,
        "label_unique_values": sorted(labels),
        "missing_rate": {column: missing[column] / row_count if row_count else None for column in headers},
        "duplicate_user_video_pairs": sum(count - 1 for count in pair_counts.values() if count > 1),
        "duplicate_user_ids": sum(count - 1 for count in user_counts.values() if count > 1),
        "duplicate_video_ids": sum(count - 1 for count in video_counts.values() if count > 1),
        "primary_key_note": "No primary key is declared by the source; duplicates are reported, not treated as errors.",
    }


def run(data_dir: str | Path, output_dir: str | Path) -> list[dict]:
    source, destination = Path(data_dir), Path(output_dir)
    available = [source / filename for filename in CSV_FILES if (source / filename).is_file()]
    if not available:
        raise FileNotFoundError(f"No known KuaiRand CSV files found in {source}; no audit numbers were created.")
    audit = [audit_csv(path) for path in available]
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "data_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    write_manifest(destination / "data_manifest.json", audit)
    return audit


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--output-dir", default="results/data_audit")
    arguments = parser.parse_args()
    report = run(arguments.data_dir, arguments.output_dir)
    print(json.dumps(report, indent=2))
