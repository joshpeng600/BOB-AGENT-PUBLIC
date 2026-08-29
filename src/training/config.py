"""Validated, resolved training configuration."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ResolvedTrainingConfig:
    seed: int = 0
    batch_size: int = 8192
    epochs: int = 40
    patience: int = 4
    max_batches: int | None = None

    def __post_init__(self) -> None:
        if self.batch_size < 1 or self.epochs < 1 or self.patience < 1:
            raise ValueError("batch_size, epochs, and patience must be positive")
        if self.max_batches is not None and self.max_batches < 1:
            raise ValueError("max_batches must be positive when provided")

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "ResolvedTrainingConfig":
        known = {"seed", "batch_size", "batch", "epochs", "epoch", "patience", "max_batches"}
        unknown = set(values).difference(known)
        if unknown:
            raise ValueError(f"unknown training config fields: {sorted(unknown)}")
        return cls(
            seed=int(values.get("seed", 0)),
            batch_size=int(values.get("batch_size", values.get("batch", 8192))),
            epochs=int(values.get("epochs", values.get("epoch", 40))),
            patience=int(values.get("patience", 4)),
            max_batches=(
                None if values.get("max_batches") is None else int(values["max_batches"])
            ),
        )

    def as_dict(self) -> dict[str, int | None]:
        return asdict(self)
