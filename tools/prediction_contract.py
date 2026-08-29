"""Strict prediction-file and evaluator-input contracts."""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Iterable, Sequence


HEADER = ["row_id", "user_id", "video_id", "score"]


class PredictionContractError(ValueError):
    """Raised when a prediction cannot be aligned safely."""


def validate_prediction_file(
    prediction_path: Path,
    expected_rows: Sequence[Sequence[object]],
) -> list[float]:
    """Validate exact row order and return finite scores.

    Official rows use indices 1 and 2 for user_id and video_id. Repeated
    user-video pairs are allowed because row_id, not the pair, is the key.
    """
    scores: list[float] = []
    try:
        handle = prediction_path.open("r", encoding="utf-8-sig", newline="")
    except FileNotFoundError as error:
        raise PredictionContractError(
            f"Prediction file does not exist: {prediction_path}"
        ) from error

    with handle:
        reader = csv.reader(handle)
        actual_header = next(reader, None)
        if actual_header != HEADER:
            raise PredictionContractError(
                f"Header must be {','.join(HEADER)}; got {actual_header}"
            )

        count = 0
        for line_number, record in enumerate(reader, start=2):
            if len(record) != 4:
                raise PredictionContractError(
                    f"Line {line_number} has {len(record)} fields; expected 4"
                )
            row_id, user_id, video_id, raw_score = record
            if row_id != str(count):
                raise PredictionContractError(
                    f"Line {line_number} row_id is {row_id!r}; expected {count}"
                )
            if count >= len(expected_rows):
                raise PredictionContractError(
                    f"Prediction is longer than the split ({len(expected_rows)} rows)"
                )

            expected_user = str(expected_rows[count][1])
            expected_video = str(expected_rows[count][2])
            if user_id != expected_user or video_id != expected_video:
                raise PredictionContractError(
                    f"Line {line_number} is misaligned: got ({user_id},{video_id}), "
                    f"expected ({expected_user},{expected_video})"
                )
            try:
                score = float(raw_score)
            except ValueError as error:
                raise PredictionContractError(
                    f"Line {line_number} score is not numeric: {raw_score!r}"
                ) from error
            if not math.isfinite(score):
                raise PredictionContractError(
                    f"Line {line_number} score must not be NaN or Inf"
                )
            scores.append(score)
            count += 1

    if count != len(expected_rows):
        raise PredictionContractError(
            f"Prediction has {count} rows; expected {len(expected_rows)}"
        )
    return scores


def validate_evaluator_arrays(
    user_ids: Iterable[object],
    labels: Iterable[object],
    scores: Iterable[object],
) -> tuple[list[str], list[int], list[float]]:
    users = [str(user) for user in user_ids]
    raw_labels = list(labels)
    raw_scores = list(scores)
    if not (len(users) == len(raw_labels) == len(raw_scores)):
        raise PredictionContractError(
            "user_ids, labels, and scores must have equal lengths"
        )
    if not users:
        raise PredictionContractError("Evaluator arrays must not be empty")
    if any(not user.strip() for user in users):
        raise PredictionContractError("user_ids must not contain empty values")

    parsed_labels: list[int] = []
    for index, label in enumerate(raw_labels):
        try:
            numeric = float(label)
        except (TypeError, ValueError) as error:
            raise PredictionContractError(
                f"Label at index {index} is not numeric: {label!r}"
            ) from error
        if numeric not in (0.0, 1.0):
            raise PredictionContractError(
                f"Label at index {index} is not binary: {label!r}"
            )
        parsed_labels.append(int(numeric))

    parsed_scores: list[float] = []
    for index, score in enumerate(raw_scores):
        try:
            numeric = float(score)
        except (TypeError, ValueError) as error:
            raise PredictionContractError(
                f"Score at index {index} is not numeric: {score!r}"
            ) from error
        if not math.isfinite(numeric):
            raise PredictionContractError(
                f"Score at index {index} must not be NaN or Inf"
            )
        parsed_scores.append(numeric)
    return users, parsed_labels, parsed_scores
