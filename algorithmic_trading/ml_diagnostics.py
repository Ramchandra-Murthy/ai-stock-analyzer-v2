"""Model diagnostics for the ML Signal Lab: is a signal real or just overfitted? (research only)

* **Out-of-sample permutation importance** shuffles one feature at a time on data the model has
  not seen and measures how much accuracy drops. In-sample importances flatter whatever the model
  memorised.
* **Time-series cross-validation** tunes hyper-parameters on forward-chained folds with a gap
  equal to the label window, so no fold trains on rows whose labels reach into its test block.
* **Train/test gap** compares in-sample with out-of-sample accuracy; a large gap is overfitting.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from algorithmic_trading.ml_signals import MODELS, build_features, build_labels
from algorithmic_trading.strategy_lab import normalise_price_frame

GRIDS: dict[str, dict[str, list]] = {
    "Logistic regression": {"C": [0.01, 0.1, 0.5, 2.0]},
    "Gradient boosting": {"max_depth": [2, 3, 4], "learning_rate": [0.03, 0.1]},
}


def make_tuned_model(name: str, **params):
    """Same families as :func:`ml_signals.make_model`, with the grid's parameters applied."""
    if name == "Logistic regression":
        return make_pipeline(
            StandardScaler(), LogisticRegression(C=params.get("C", 0.5), max_iter=500)
        )
    if name == "Gradient boosting":
        return HistGradientBoostingClassifier(
            max_depth=params.get("max_depth", 3),
            learning_rate=params.get("learning_rate", 0.05),
            max_iter=150,
            random_state=0,
        )
    raise ValueError(f"Unknown model: {name}")


def accuracy(model, x: pd.DataFrame, y: pd.Series) -> float:
    return float((model.predict(x) == y).mean())


def permutation_importance_oos(
    model, x: pd.DataFrame, y: pd.Series, *, n_repeats: int = 10, seed: int = 0
) -> pd.DataFrame:
    """Accuracy lost when each feature is shuffled on held-out ``x``, ``y`` (mean and std)."""
    if n_repeats < 1 or len(x) < 30:
        raise ValueError("Need n_repeats >= 1 and at least 30 held-out rows.")
    rng = np.random.default_rng(seed)
    base = accuracy(model, x, y)
    rows = {}
    for column in x.columns:
        drops = []
        for _ in range(n_repeats):
            shuffled = x.copy()
            shuffled[column] = rng.permutation(shuffled[column].to_numpy())
            drops.append(base - accuracy(model, shuffled, y))
        rows[column] = {"importance": float(np.mean(drops)), "std": float(np.std(drops))}
    return pd.DataFrame(rows).T.sort_values("importance", ascending=False)


def time_series_grid_search(
    factory: Callable[..., object],
    grid: Mapping[str, Sequence],
    x: pd.DataFrame,
    y: pd.Series,
    *,
    n_splits: int = 4,
    gap: int = 0,
) -> pd.DataFrame:
    """Score every parameter combination on forward-chained folds, best first."""
    if n_splits < 2 or gap < 0 or not grid:
        raise ValueError("Need n_splits >= 2, gap >= 0 and a non-empty grid.")
    if len(x) < (n_splits + 1) * 30:
        raise ValueError("Too little data for this many folds.")
    names = list(grid)
    splitter = TimeSeriesSplit(n_splits=n_splits, gap=gap)
    rows = []
    for values in itertools.product(*(grid[n] for n in names)):
        params = dict(zip(names, values, strict=True))
        test_scores, train_scores = [], []
        for train_idx, test_idx in splitter.split(x):
            model = factory(**params)
            model.fit(x.iloc[train_idx], y.iloc[train_idx])  # type: ignore[attr-defined]
            test_scores.append(accuracy(model, x.iloc[test_idx], y.iloc[test_idx]))
            train_scores.append(accuracy(model, x.iloc[train_idx], y.iloc[train_idx]))
        rows.append(
            {
                **params,
                "cv_accuracy": float(np.mean(test_scores)),
                "cv_std": float(np.std(test_scores)),
                "train_accuracy": float(np.mean(train_scores)),
            }
        )
    return pd.DataFrame(rows).sort_values("cv_accuracy", ascending=False).reset_index(drop=True)


def overfit_verdict(train_accuracy: float, test_accuracy: float, base_rate: float) -> str:
    """Plain-language reading of the train/test gap and of the edge over the base rate."""
    gap = train_accuracy - test_accuracy
    edge = test_accuracy - base_rate
    if gap > 0.15:
        return "Severe overfitting: it fits the past far better than unseen data."
    if gap > 0.07:
        return "Moderate overfitting: expect live results below the in-sample numbers."
    if edge <= 0.01:
        return "No real edge: unseen-data accuracy is no better than the always-up base rate."
    return "Small train/test gap and a measurable edge, but one test period is weak evidence."


@dataclass(frozen=True)
class Diagnosis:
    train_accuracy: float
    test_accuracy: float
    base_rate: float
    verdict: str
    importances: pd.DataFrame
    grid: pd.DataFrame
    best_params: dict
    train_rows: int
    test_rows: int


def diagnose_model(
    frame: pd.DataFrame,
    *,
    model: str = "Logistic regression",
    horizon: int = 5,
    test_fraction: float = 0.3,
    n_splits: int = 4,
    n_repeats: int = 10,
) -> Diagnosis:
    """Tune on the early part of the history, then judge once on the untouched later part."""
    if model not in MODELS:
        raise ValueError(f"Unknown model: {model}")
    if not 0.1 <= test_fraction <= 0.5:
        raise ValueError("test_fraction must be between 0.1 and 0.5.")
    data = normalise_price_frame(frame)
    feats, labels = build_features(data), build_labels(data["Close"], horizon)
    keep = feats.notna().all(axis=1) & labels.notna()
    x, y = feats[keep], labels[keep].astype(int)
    if len(x) < 400:
        raise ValueError("Need at least 400 clean rows for diagnostics.")
    cut = int(len(x) * (1.0 - test_fraction))
    gap = 2 * horizon  # label window plus an embargo
    x_train, y_train = x.iloc[: cut - gap], y.iloc[: cut - gap]
    x_test, y_test = x.iloc[cut:], y.iloc[cut:]
    grid = time_series_grid_search(
        lambda **p: make_tuned_model(model, **p),
        GRIDS[model],
        x_train,
        y_train,
        n_splits=n_splits,
        gap=gap,
    )
    best = {k: grid.iloc[0][k] for k in GRIDS[model]}
    best = {
        k: (int(v) if float(v).is_integer() and k == "max_depth" else float(v))
        for k, v in best.items()
    }
    fitted = make_tuned_model(model, **best).fit(x_train, y_train)  # type: ignore[attr-defined]
    train_acc, test_acc = accuracy(fitted, x_train, y_train), accuracy(fitted, x_test, y_test)
    up = float(y_test.mean())
    base = max(up, 1.0 - up)
    return Diagnosis(
        train_accuracy=train_acc,
        test_accuracy=test_acc,
        base_rate=base,
        verdict=overfit_verdict(train_acc, test_acc, base),
        importances=permutation_importance_oos(fitted, x_test, y_test, n_repeats=n_repeats),
        grid=grid,
        best_params=best,
        train_rows=len(x_train),
        test_rows=len(x_test),
    )
