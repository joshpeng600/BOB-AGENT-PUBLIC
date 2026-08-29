from __future__ import annotations

import csv
from pathlib import Path


LOG_HEADER = ["date", "user_id", "video_id", "tab", "duration_ms", "long_view"]


def write_csv(path: Path, header: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def make_dataset(root: Path, include_test: bool = False) -> Path:
    write_csv(
        root / "video_features_basic_pure.csv",
        ["video_id", "author_id"],
        [["v1", "a1"], ["v2", "a2"]],
    )
    write_csv(
        root / "log_standard_4_08_to_4_21_pure.csv",
        LOG_HEADER,
        [
            [20220408, "u1", "v1", 1, 1000, 0],
            [20220409, "u2", "v2", 1, 2000, 1],
        ],
    )
    valid_rows = [
        [20220422, "u1", "v1", 1, 1000, 1],
        [20220423, "u1", "v2", 1, 2000, 0],
    ]
    if include_test:
        valid_rows.append([20220429, "u2", "v1", 1, 1000, 1])
    write_csv(root / "log_standard_4_22_to_5_08_pure.csv", LOG_HEADER, valid_rows)
    return root
