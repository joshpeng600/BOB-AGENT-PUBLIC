"""Reproducible NumPy FM matching the official pointwise implementation."""
from __future__ import annotations

import numpy as np


def sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(values, -30, 30)))


class FactorizationMachine:
    """Factorization Machine with the official Adam/SGD update behaviour."""

    def __init__(
        self,
        feature_dim: int,
        embedding_dim: int = 16,
        learning_rate: float = 0.001,
        l2: float = 1e-6,
        seed: int = 0,
    ) -> None:
        if feature_dim < 1 or embedding_dim < 1:
            raise ValueError("feature_dim and embedding_dim must be positive")
        rng = np.random.default_rng(seed)
        self.V = rng.normal(0, 0.01, (feature_dim, embedding_dim)).astype(np.float32)
        self.W = np.zeros(feature_dim, dtype=np.float32)
        self.b = np.float32(0.0)
        self.learning_rate = float(learning_rate)
        self.l2 = float(l2)
        self.mV = np.zeros_like(self.V)
        self.vV = np.zeros_like(self.V)
        self.mW = np.zeros_like(self.W)
        self.vW = np.zeros_like(self.W)
        self.t = 0

    def logits(self, features: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        features = self._validate_features(features)
        embeddings = self.V[features]
        summed = embeddings.sum(axis=1)
        interactions = 0.5 * (
            (summed**2).sum(axis=1) - (embeddings**2).sum(axis=(1, 2))
        )
        return self.b + self.W[features].sum(axis=1) + interactions, embeddings, summed

    def step(self, features: np.ndarray, labels: np.ndarray) -> float:
        labels = self._validate_labels(labels, len(features))
        if len(labels) == 0:
            raise ValueError("pointwise batch must contain at least one row")
        scores, embeddings, summed = self.logits(features)
        gradient = ((sigmoid(scores) - labels) / len(labels)).astype(np.float32)
        grad_v = np.zeros_like(self.V)
        grad_w = np.zeros_like(self.W)
        np.add.at(grad_w, features, gradient[:, None])
        np.add.at(
            grad_v,
            features,
            gradient[:, None, None] * (summed[:, None, :] - embeddings),
        )
        self._apply_adam(grad_v + self.l2 * self.V, grad_w + self.l2 * self.W)
        self.b -= self.learning_rate * gradient.sum()
        probabilities = sigmoid(scores)
        return float(
            -np.mean(
                labels * np.log(probabilities + 1e-9)
                + (1 - labels) * np.log(1 - probabilities + 1e-9)
            )
        )

    def pairwise_step(self, positive: np.ndarray, negative: np.ndarray) -> float:
        """Optimize -log(sigmoid(score_pos-score_neg)) for aligned pairs."""
        if len(positive) != len(negative):
            raise ValueError("positive and negative batches must have equal length")
        if len(positive) == 0:
            raise ValueError("BPR batch must contain at least one valid pair")
        pos_scores, pos_embeddings, pos_summed = self.logits(positive)
        neg_scores, neg_embeddings, neg_summed = self.logits(negative)
        difference = pos_scores - neg_scores
        gradient = ((sigmoid(difference) - 1.0) / len(difference)).astype(np.float32)
        grad_v = np.zeros_like(self.V)
        grad_w = np.zeros_like(self.W)
        np.add.at(grad_w, positive, gradient[:, None])
        np.add.at(grad_w, negative, -gradient[:, None])
        np.add.at(
            grad_v,
            positive,
            gradient[:, None, None] * (pos_summed[:, None, :] - pos_embeddings),
        )
        np.add.at(
            grad_v,
            negative,
            -gradient[:, None, None] * (neg_summed[:, None, :] - neg_embeddings),
        )
        self._apply_adam(grad_v + self.l2 * self.V, grad_w + self.l2 * self.W)
        return float(np.mean(np.logaddexp(0.0, -difference)))

    def predict_scores(self, features: np.ndarray, batch_size: int = 200_000) -> np.ndarray:
        features = self._validate_features(features)
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        if len(features) == 0:
            return np.empty(0, dtype=np.float32)
        chunks = [
            self.logits(features[start : start + batch_size])[0]
            for start in range(0, len(features), batch_size)
        ]
        scores = np.concatenate(chunks)
        if len(scores) != len(features):
            raise RuntimeError("predict_scores violated the one-score-per-row contract")
        if not np.isfinite(scores).all():
            raise FloatingPointError("predict_scores produced NaN or Inf")
        return scores

    predict = predict_scores

    def state_dict(self) -> dict[str, np.ndarray]:
        return {
            "V": self.V.copy(),
            "W": self.W.copy(),
            "b": np.asarray(self.b, dtype=np.float32),
            "mV": self.mV.copy(),
            "vV": self.vV.copy(),
            "mW": self.mW.copy(),
            "vW": self.vW.copy(),
            "t": np.asarray(self.t, dtype=np.int64),
        }

    def load_state_dict(self, state: dict[str, np.ndarray]) -> None:
        required = {"V", "W", "b", "mV", "vV", "mW", "vW", "t"}
        missing = required.difference(state)
        if missing:
            raise ValueError(f"checkpoint is missing state fields: {sorted(missing)}")
        for name in ("V", "W", "mV", "vV", "mW", "vW"):
            current = getattr(self, name)
            incoming = np.asarray(state[name])
            if incoming.shape != current.shape:
                raise ValueError(
                    f"checkpoint shape mismatch for {name}: expected {current.shape}, got {incoming.shape}"
                )
            current[...] = incoming.astype(current.dtype, copy=False)
        self.b = np.float32(np.asarray(state["b"]).item())
        self.t = int(np.asarray(state["t"]).item())

    def _apply_adam(self, grad_v: np.ndarray, grad_w: np.ndarray) -> None:
        self.t += 1
        beta1, beta2, epsilon = 0.9, 0.999, 1e-8
        for parameter, gradient, first, second in (
            (self.V, grad_v, self.mV, self.vV),
            (self.W, grad_w, self.mW, self.vW),
        ):
            first *= beta1
            first += (1 - beta1) * gradient
            second *= beta2
            second += (1 - beta2) * (gradient * gradient)
            parameter -= self.learning_rate * (
                first / (1 - beta1**self.t)
            ) / (np.sqrt(second / (1 - beta2**self.t)) + epsilon)

    def _validate_features(self, features: np.ndarray) -> np.ndarray:
        array = np.asarray(features)
        if array.ndim != 2:
            raise ValueError(f"features must be a 2D array, got shape {array.shape}")
        if not np.issubdtype(array.dtype, np.integer):
            raise TypeError("features must contain integer feature indexes")
        if array.size and (array.min() < 0 or array.max() >= len(self.W)):
            raise ValueError("feature index is outside the model feature dimension")
        return array

    @staticmethod
    def _validate_labels(labels: np.ndarray, expected_rows: int) -> np.ndarray:
        array = np.asarray(labels, dtype=np.float32)
        if array.ndim != 1 or len(array) != expected_rows:
            raise ValueError("labels must be a 1D array aligned with feature rows")
        if not np.isin(array, (0.0, 1.0)).all():
            raise ValueError("labels must contain only 0 and 1")
        return array
