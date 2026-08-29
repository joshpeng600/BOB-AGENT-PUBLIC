"""Training contracts owned by Track 2 role D."""

from .config import ResolvedTrainingConfig
from .trainer import TrainResult, fit_pointwise

__all__ = ["ResolvedTrainingConfig", "TrainResult", "fit_pointwise"]
