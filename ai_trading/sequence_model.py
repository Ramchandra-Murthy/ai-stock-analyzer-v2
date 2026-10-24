"""Leakage-safe sequence learning engine for AI trading research."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.preprocessing import StandardScaler

from ai_trading.features import build_features
from ai_trading.ml_model import FEATURE_COLUMNS, make_training_dataset


@dataclass(frozen=True)
class SequenceValidation:
    accuracy: float
    roc_auc: float | None
    train_samples: int
    test_samples: int
    positive_rate: float


def _make_raw_sequences(
    frame: pd.DataFrame,
    *,
    sequence_length: int,
    horizon: int,
    threshold: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build unscaled sequences, labels, and original frame positions."""
    if sequence_length < 2:
        raise ValueError("sequence_length must be at least 2")

    features, labels = make_training_dataset(
        frame,
        horizon=horizon,
        threshold=threshold,
    )
    if len(features) < sequence_length:
        raise ValueError("not enough samples for sequence training")

    values = features[FEATURE_COLUMNS].to_numpy(dtype=float)
    x = np.asarray(
        [values[i - sequence_length + 1 : i + 1] for i in range(sequence_length - 1, len(values))],
        dtype=float,
    )
    positions = frame.index.get_indexer(features.index)
    end_positions = positions[sequence_length - 1 :]
    y = labels.iloc[sequence_length - 1 :].to_numpy(dtype=int)
    return x, y, end_positions


def make_sequences(
    frame: pd.DataFrame,
    *,
    sequence_length: int = 20,
    horizon: int = 5,
    threshold: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Build chronological fixed-length feature sequences and labels.

    Features are returned unscaled so callers can fit preprocessing only on
    their training window and then apply the same transform to validation data.
    """
    x, y, _ = _make_raw_sequences(
        frame,
        sequence_length=sequence_length,
        horizon=horizon,
        threshold=threshold,
    )
    return x, y


def train_sequence_model(
    frame: pd.DataFrame,
    *,
    sequence_length: int = 20,
    horizon: int = 5,
    threshold: float = 0.0,
    test_fraction: float = 0.2,
) -> tuple[dict[str, object], SequenceValidation]:
    """Train a sequence model with purged chronological validation."""
    if not 0.1 <= test_fraction < 0.5:
        raise ValueError("test_fraction must be between 0.1 and 0.5")

    x, y, positions = _make_raw_sequences(
        frame,
        sequence_length=sequence_length,
        horizon=horizon,
        threshold=threshold,
    )
    split = max(1, int(len(x) * (1.0 - test_fraction)))
    if split >= len(x):
        raise ValueError("test split leaves no validation samples")

    validation_start = positions[split]
    train_mask = positions[:split] + horizon < validation_start
    train_x, test_x = x[:split][train_mask], x[split:]
    train_y, test_y = y[:split][train_mask], y[split:]
    if len(train_x) < 20 or len(test_x) < 5:
        raise ValueError("training and test windows are too small after purging overlapping labels")
    if np.unique(train_y).size < 2:
        raise ValueError("training data must contain both classes")

    scaler = StandardScaler()
    train_flat = train_x.reshape(-1, train_x.shape[-1])
    scaler.fit(train_flat)
    train_x = scaler.transform(train_flat).reshape(train_x.shape)
    test_x = scaler.transform(test_x.reshape(-1, test_x.shape[-1])).reshape(test_x.shape)

    from sklearn.neural_network import MLPClassifier

    model = MLPClassifier(
        hidden_layer_sizes=(32, 16),
        max_iter=500,
        random_state=42,
        # Validation is handled by the chronological holdout above. Avoid
        # MLPClassifier's internal random early-stopping split.
        early_stopping=False,
    )
    model.fit(train_x.reshape(len(train_x), -1), train_y)
    probabilities = model.predict_proba(test_x.reshape(len(test_x), -1))[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    accuracy = float(accuracy_score(test_y, predictions))
    roc_auc = float(roc_auc_score(test_y, probabilities)) if np.unique(test_y).size > 1 else None
    validation = SequenceValidation(
        accuracy=accuracy,
        roc_auc=roc_auc,
        train_samples=len(train_x),
        test_samples=len(test_x),
        positive_rate=float(y.mean()),
    )
    return {"model": model, "scaler": scaler}, validation


def predict_sequence(
    trained: dict[str, object],
    frame: pd.DataFrame,
    *,
    sequence_length: int = 20,
) -> dict[str, float | str]:
    """Predict the latest sequence using the training-fitted scaler."""
    if sequence_length < 2:
        raise ValueError("sequence_length must be at least 2")

    features = build_features(frame)[FEATURE_COLUMNS].dropna()
    if len(features) < sequence_length:
        raise ValueError("not enough market history for a prediction")

    raw_sequence = features.iloc[-sequence_length:].to_numpy(dtype=float)
    scaler = trained["scaler"]
    scaled_sequence = scaler.transform(raw_sequence)
    model = trained["model"]
    probabilities = model.predict_proba(scaled_sequence.reshape(1, -1))[:, 1]
    probability = float(probabilities[0])
    return {
        "probability_up": probability,
        "confidence": abs(probability - 0.5) * 2.0,
        "signal": "LONG" if probability >= 0.5 else "SHORT",
    }
