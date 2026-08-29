"""Stable, time-safe data contract for Track 2 development.

The official baseline uses a seven-position tuple.  This module names those
positions while retaining tuple behaviour and preserves source-file order.
It intentionally exposes development splits only by default.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import NamedTuple

LABEL = "long_view"
DEV_MAX_DATE = 20220428
DEV_SPLITS = {"train": (20220408, 20220421), "valid": (20220422, DEV_MAX_DATE)}
OFFICIAL_SPLITS = {**DEV_SPLITS, "test": (20220429, 20220508)}
LOG_FILES = ("log_standard_4_08_to_4_21_pure.csv", "log_standard_4_22_to_5_08_pure.csv")


class RawInteraction(NamedTuple):
    """Official raw row contract; indices 0..6 match baseline/data.py exactly."""

    date: int          # [0], int
    user_id: str       # [1], string identifier
    video_id: str      # [2], string identifier
    author_id: str     # [3], string identifier or "UNK"
    tab: str           # [4], string category
    duration_ms: float # [5], float
    long_view: int     # [6], 0 or 1


def _video_to_author(data_dir: Path) -> dict[str, str]:
    with (data_dir / "video_features_basic_pure.csv").open(newline="") as handle:
        return {row["video_id"]: row["author_id"] for row in csv.DictReader(handle)}


def load_raw_rows(data_dir: str | Path) -> list[RawInteraction]:
    """Read official logs in the official file order; do not sort or deduplicate."""
    root = Path(data_dir)
    authors = _video_to_author(root)
    rows: list[RawInteraction] = []
    for filename in LOG_FILES:
        with (root / filename).open(newline="") as handle:
            for row in csv.DictReader(handle):
                rows.append(
                    RawInteraction(
                        int(row["date"]), row["user_id"], row["video_id"],
                        authors.get(row["video_id"], "UNK"), row["tab"],
                        float(row["duration_ms"]), 1 if row[LABEL] != "0" else 0,
                    )
                )
    return rows


def load_dev_splits(data_dir: str | Path) -> dict[str, list[RawInteraction]]:
    """Return train and valid only. Test is deliberately unavailable to developers."""
    rows = load_raw_rows(data_dir)
    return {
        name: [row for row in rows if lower <= row.date <= upper]
        for name, (lower, upper) in DEV_SPLITS.items()
    }


def split_name(date: int) -> str | None:
    """Classify a date without reading labels or scores."""
    for name, (lower, upper) in OFFICIAL_SPLITS.items():
        if lower <= date <= upper:
            return name
    return None
