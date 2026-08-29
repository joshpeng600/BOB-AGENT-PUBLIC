"""Portable NumPy checkpoint format with JSON metadata and no pickle."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from src.models.fm import FactorizationMachine


FORMAT_VERSION = 1


def save_checkpoint(
    path: str | Path,
    model: FactorizationMachine,
    *,
    config: dict[str, Any],
    epoch: int,
    best_metric: float | None,
) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "format_version": FORMAT_VERSION,
        "model_class": "FactorizationMachine",
        "feature_dim": int(model.V.shape[0]),
        "embedding_dim": int(model.V.shape[1]),
        "learning_rate": model.learning_rate,
        "l2": model.l2,
        "config": config,
        "epoch": int(epoch),
        "best_metric": best_metric,
    }
    np.savez_compressed(
        destination,
        metadata=np.asarray(json.dumps(metadata, sort_keys=True)),
        **model.state_dict(),
    )


def load_checkpoint(path: str | Path) -> tuple[FactorizationMachine, dict[str, Any]]:
    with np.load(Path(path), allow_pickle=False) as payload:
        metadata = json.loads(str(payload["metadata"].item()))
        if metadata.get("format_version") != FORMAT_VERSION:
            raise ValueError("unsupported checkpoint format_version")
        if metadata.get("model_class") != "FactorizationMachine":
            raise ValueError("checkpoint does not contain a FactorizationMachine")
        model = FactorizationMachine(
            feature_dim=int(metadata["feature_dim"]),
            embedding_dim=int(metadata["embedding_dim"]),
            learning_rate=float(metadata["learning_rate"]),
            l2=float(metadata["l2"]),
        )
        model.load_state_dict({name: payload[name] for name in payload.files if name != "metadata"})
    return model, metadata
