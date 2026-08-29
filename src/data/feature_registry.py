"""Feature metadata and guardrails.  Add a registry entry before adding a feature."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    source_columns: tuple[str, ...]
    fit_split: str
    time_available_at: str
    dtype: str
    dimensions: int
    missing_strategy: str
    within_user_constant: bool = False

    def validate(self) -> None:
        if self.fit_split != "train":
            raise ValueError(f"{self.name}: vocabularies, buckets, and statistics must fit train only")
        if self.dimensions < 1:
            raise ValueError(f"{self.name}: dimensions must be positive")
        if self.time_available_at not in {"impression", "strictly_before_impression"}:
            raise ValueError(f"{self.name}: invalid time availability")


FEATURE_REGISTRY = (
    FeatureSpec("user_id", ("user_id",), "train", "impression", "categorical", 1, "UNK", True),
    FeatureSpec("video_id", ("video_id",), "train", "impression", "categorical", 1, "UNK"),
    FeatureSpec("author_id", ("video_id", "author_id"), "train", "impression", "categorical", 1, "UNK"),
    FeatureSpec("tab", ("tab",), "train", "impression", "categorical", 1, "UNK"),
    FeatureSpec("dur_bucket", ("duration_ms",), "train", "impression", "categorical", 1, "UNK"),
)


def validate_registry(registry: tuple[FeatureSpec, ...] = FEATURE_REGISTRY) -> None:
    names = set()
    for feature in registry:
        feature.validate()
        if feature.name in names:
            raise ValueError(f"duplicate feature: {feature.name}")
        names.add(feature.name)
