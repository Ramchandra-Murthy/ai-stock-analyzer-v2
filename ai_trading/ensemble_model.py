"""Leakage-safe ensemble machine-learning engine for AI trading research."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ai_trading.ml_model import FEATURE_COLUMNS, make_training_dataset


@dataclass(frozen=True)
class EnsembleValidation:
    """Chronological validation metrics for the ensemble."""

    accuracy: float
    roc_auc: float | None
    train_samples: int
    test_samples: int
    positive_rate: float


def _models(random_state: int) -> dict[str, object]:
    return {
        "logistic_regression": Pipeline(
            [
                ("scaler", StandardScaler()),
                ("model", LogisticRegression(max_iter=1000)),
            ]
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=100,
            max_depth=5,
            min_samples_leaf=3,
            random_state=random_state,
        ),
    }


def train_ensemble(
    frame: pd.DataFrame,
    *,
    horizon: int = 5,
    threshold: float = 0.0,
    test_fraction: float = 0.2,
    random_state: int = 42,
) -> tuple[dict[str, object], EnsembleValidation]:
    """Train an ensemble using chronological train/test data only."""
    x, y = make_training_dataset(
        frame,
        horizon=horizon,
        threshold=threshold,
    )
    if len(x) < 20:
        raise ValueError("not enough samples for ensemble training")
    if not 0.1 <= test_fraction < 0.5:
        raise ValueError("test_fraction must be between 0.1 and 0.5")

    split = max(1, int(len(x) * (1.0 - test_fraction)))
    if split >= len(x):
        raise ValueError("test split leaves no validation samples")

    train_x, test_x = x.iloc[:split], x.iloc[split:]
    train_y, test_y = y.iloc[:split], y.iloc[split:]
    if train_y.nunique() < 2:
        raise ValueError("ensemble training requires both target classes in the training window")

    models = _models(random_state)
    for model in models.values():
        model.fit(train_x[FEATURE_COLUMNS], train_y)

    probabilities = [
        model.predict_proba(test_x[FEATURE_COLUMNS])[:, 1] for model in models.values()
    ]
    ensemble_probability = sum(probabilities) / len(probabilities)
    predictions = (ensemble_probability >= 0.5).astype(int)
    accuracy = float(accuracy_score(test_y, predictions))
    roc_auc = float(roc_auc_score(test_y, ensemble_probability)) if test_y.nunique() > 1 else None
    validation = EnsembleValidation(
        accuracy=accuracy,
        roc_auc=roc_auc,
        train_samples=len(train_x),
        test_samples=len(test_x),
        positive_rate=float(y.mean()),
    )
    return models, validation


def predict_ensemble(
    models: dict[str, object],
    frame: pd.DataFrame,
) -> dict[str, float | str]:
    """Average model probabilities into one ensemble prediction."""
    x, _ = make_training_dataset(frame, horizon=1, threshold=0.0)
    if x.empty:
        raise ValueError("not enough data for ensemble prediction")
    probabilities = [
        float(model.predict_proba(x[FEATURE_COLUMNS].iloc[[-1]])[:, 1][0])
        for model in models.values()
    ]
    probability = sum(probabilities) / len(probabilities)
    signal = "LONG" if probability >= 0.5 else "SHORT"
    confidence = abs(probability - 0.5) * 2.0
    return {
        "probability_up": probability,
        "confidence": confidence,
        "signal": signal,
    }
