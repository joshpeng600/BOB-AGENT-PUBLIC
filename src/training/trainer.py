"""Deterministic pointwise trainer; metric computation stays outside role D."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from src.models.base import RankingModel
from src.training.config import ResolvedTrainingConfig


@dataclass(frozen=True)
class TrainResult:
    epochs_ran: int
    best_epoch: int
    best_metric: float
    train_losses: tuple[float, ...]
    validation_metrics: tuple[float, ...]


def fit_pointwise(
    model: RankingModel,
    train_features: np.ndarray,
    train_labels: np.ndarray,
    valid_features: np.ndarray,
    validation_metric: Callable[[np.ndarray], float],
    config: ResolvedTrainingConfig,
) -> TrainResult:
    """Train on train rows and select state only with a caller-supplied valid metric."""
    if len(train_features) != len(train_labels) or len(train_labels) == 0:
        raise ValueError("training features and labels must be non-empty and aligned")
    rng = np.random.default_rng(config.seed)
    best_metric = -np.inf
    best_epoch = 0
    best_state: dict[str, np.ndarray] | None = None
    bad_epochs = 0
    train_losses: list[float] = []
    valid_metrics: list[float] = []

    for epoch in range(1, config.epochs + 1):
        order = rng.permutation(len(train_labels))
        losses: list[float] = []
        for batch_number, start in enumerate(range(0, len(order), config.batch_size)):
            if config.max_batches is not None and batch_number >= config.max_batches:
                break
            indexes = order[start : start + config.batch_size]
            losses.append(model.step(train_features[indexes], train_labels[indexes]))
        if not losses:
            raise RuntimeError("training produced no batches")
        score = float(validation_metric(model.predict_scores(valid_features)))
        if not np.isfinite(score):
            raise FloatingPointError("validation metric must be finite")
        train_losses.append(float(np.mean(losses)))
        valid_metrics.append(score)
        if score > best_metric + 1e-5:
            best_metric = score
            best_epoch = epoch
            best_state = model.state_dict()
            bad_epochs = 0
        else:
            bad_epochs += 1
            if bad_epochs >= config.patience:
                break

    if best_state is None:
        raise RuntimeError("training did not produce a best model state")
    model.load_state_dict(best_state)
    return TrainResult(
        epochs_ran=len(train_losses),
        best_epoch=best_epoch,
        best_metric=best_metric,
        train_losses=tuple(train_losses),
        validation_metrics=tuple(valid_metrics),
    )
