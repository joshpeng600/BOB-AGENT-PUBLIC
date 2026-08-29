"""Generate a compact Markdown summary from reports/experiments.csv."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


REQUIRED_COLUMNS = [
    "experiment_id",
    "hypothesis",
    "code_change",
    "gauc",
    "ndcg5",
    "primary_score",
    "error",
    "recovery",
    "manual_intervention",
    "tokens",
    "wall_time",
    "gpu_usage",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("reports/experiments.csv"))
    parser.add_argument("--output", type=Path, default=Path("reports/results_summary.md"))
    args = parser.parse_args()

    with args.input.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != REQUIRED_COLUMNS:
            print("SUMMARY FAILED: experiments.csv header does not match the contract")
            return 1
        rows = list(reader)

    valid_rows = []
    for row in rows:
        try:
            primary = float(row["primary_score"])
        except (TypeError, ValueError):
            continue
        valid_rows.append((primary, row))
    valid_rows.sort(key=lambda item: item[0], reverse=True)

    lines = [
        "# Experiment results",
        "",
        f"Recorded experiments: **{len(rows)}**",
        f"Experiments with numeric primary score: **{len(valid_rows)}**",
        "",
        "| Rank | Experiment | Hypothesis | GAUC | nDCG@5 | Primary |",
        "|---:|---|---|---:|---:|---:|",
    ]
    for rank, (_, row) in enumerate(valid_rows, start=1):
        hypothesis = row["hypothesis"].replace("|", "\\|")
        lines.append(
            f"| {rank} | {row['experiment_id']} | {hypothesis} | "
            f"{row['gauc']} | {row['ndcg5']} | {row['primary_score']} |"
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
