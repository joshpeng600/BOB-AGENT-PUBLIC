"""Minimal same-user BPR pair sampling and training support."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.models.fm import FactorizationMachine
from src.training.config import ResolvedTrainingConfig


@dataclass(frozen=True)
class PairCoverage:
    total_users: int
    eligible_users: int
    pairs: int

    @property
    def user_coverage(self) -> float:
        return self.eligible_users / self.total_users if self.total_users else 0.0


def sample_same_user_pairs(
    user_ids: list[str] | np.ndarray,
    labels: np.ndarray,
    *,
    negatives_per_positive: int = 1,
    seed: int = 0,
) -> tuple[np.ndarray, np.ndarray, PairCoverage]:
    """Return aligned positive/negative row indexes sampled within each user."""
    users = np.asarray(user_ids)
    labels = np.asarray(labels)
    if users.ndim != 1 or labels.ndim != 1 or len(users) != len(labels):
        raise ValueError("user_ids and labels must be aligned 1D arrays")
    if not np.isin(labels, (0, 1)).all():
        raise ValueError("labels must contain only 0 and 1")
    if negatives_per_positive < 1:
        raise ValueError("negatives_per_positive must be positive")
    rng = np.random.default_rng(seed)
    groups: dict[str, list[int]] = {}
    for index, user in enumerate(users.tolist()):
        groups.setdefault(str(user), []).append(index)
    positive_indexes: list[int] = []
    negative_indexes: list[int] = []
    eligible_users = 0
    for indexes in groups.values():
        positives = np.asarray([i for i in indexes if labels[i] == 1], dtype=np.int64)
        negatives = np.asarray([i for i in indexes if labels[i] == 0], dtype=np.int64)
        if len(positives) == 0 or len(negatives) == 0:
            continue
        eligible_users += 1
        for positive in positives:
            sampled = rng.choice(negatives, size=negatives_per_positive, replace=True)
            positive_indexes.extend([int(positive)] * negatives_per_positive)
            negative_indexes.extend(int(index) for index in sampled)
    coverage = PairCoverage(len(groups), eligible_users, len(positive_indexes))
    if not positive_indexes:
        raise ValueError(
            "no valid BPR pairs: every user is all-positive, all-negative, or the input is empty"
        )
    return (
        np.asarray(positive_indexes, dtype=np.int64),
        np.asarray(negative_indexes, dtype=np.int64),
        coverage,
    )


def fit_bpr_epoch(
    model: FactorizationMachine,
    features: np.ndarray,
    labels: np.ndarray,
    user_ids: list[str] | np.ndarray,
    config: ResolvedTrainingConfig,
    *,
    negatives_per_positive: int = 1,
    epoch: int = 0,
) -> tuple[float, PairCoverage]:
    """Run one reproducible BPR epoch and return mean loss plus pair coverage."""
    positive, negative, coverage = sample_same_user_pairs(
        user_ids,
        labels,
        negatives_per_positive=negatives_per_positive,
        seed=config.seed + epoch,
    )
    rng = np.random.default_rng(config.seed + epoch)
    order = rng.permutation(len(positive))
    losses: list[float] = []
    for batch_number, start in enumerate(range(0, len(order), config.batch_size)):
        if config.max_batches is not None and batch_number >= config.max_batches:
            break
        indexes = order[start : start + config.batch_size]
        losses.append(model.pairwise_step(features[positive[indexes]], features[negative[indexes]]))
    if not losses:
        raise RuntimeError("BPR training produced no batches")
    return float(np.mean(losses)), coverage
