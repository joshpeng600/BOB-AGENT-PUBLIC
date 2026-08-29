"""Small model contract shared by training and experiment runners."""
from __future__ import annotations

from typing import Protocol

import numpy as np


class RankingModel(Protocol):
    """A model that trains on aligned rows and scores them without reordering."""

    def step(self, features: np.ndarray, labels: np.ndarray) -> float:
        """Run one pointwise optimization step and return its scalar loss."""

    def predict_scores(self, features: np.ndarray, batch_size: int = 200_000) -> np.ndarray:
        """Return one finite score per input row in the original row order."""

    def state_dict(self) -> dict[str, np.ndarray]:
        """Return all parameters and optimizer state needed for exact resumption."""

    def load_state_dict(self, state: dict[str, np.ndarray]) -> None:
        """Restore parameters and optimizer state after validating shapes."""
