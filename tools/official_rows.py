"""Dependency-free loader for the official split row order used by the gate."""

from __future__ import annotations

import csv
from pathlib import Path


SPLITS = {
    "train": (20220408, 20220421),
    "valid": (20220422, 20220428),
    "test": (20220429, 20220508),
}
LOG_FILES = (
    "log_standard_4_08_to_4_21_pure.csv",
    "log_standard_4_22_to_5_08_pure.csv",
)
REQUIRED_COLUMNS = {"date", "user_id", "video_id", "long_view"}


def load_splits(data_dir: Path) -> dict[str, list[tuple[object, ...]]]:
    """Load row identity and labels in the same deterministic official order."""
    rows: list[tuple[object, ...]] = []
    for filename in LOG_FILES:
        path = data_dir / filename
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            missing = REQUIRED_COLUMNS.difference(reader.fieldnames or [])
            if missing:
                raise ValueError(f"{path} is missing columns: {sorted(missing)}")
            for line_number, record in enumerate(reader, start=2):
                try:
                    date = int(record["date"])
                except (TypeError, ValueError) as error:
                    raise ValueError(
                        f"{path}:{line_number} has an invalid date"
                    ) from error
                user_id = record["user_id"]
                video_id = record["video_id"]
                label = 1 if record["long_view"] != "0" else 0
                # Preserve the official tuple positions used by starter/data.py:
                # date=0, user_id=1, video_id=2, long_view=6.
                rows.append((date, user_id, video_id, None, None, None, label))

    return {
        split: [row for row in rows if lower <= row[0] <= upper]
        for split, (lower, upper) in SPLITS.items()
    }
