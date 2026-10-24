"""Feature-distribution drift detection for AI trading research."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ai_trading.features import build_features
from ai_trading.ml_model import FEATURE_COLUMNS


@dataclass(frozen=True)
class FeatureDrift:
    feature: str
    baseline_mean: float
    current_mean: float
    baseline_std: float
    mean_shift_pct: float
    drift_score: float
    drifted: bool


def _numeric(frame: pd.DataFrame, feature: str) -> pd.Series:
    return (
        pd.to_numeric(frame[feature], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    )


def compare_feature_drift(
    baseline: pd.DataFrame,
    current: pd.DataFrame,
    *,
    threshold: float = 2.0,
) -> pd.DataFrame:
    """Compare current feature means with a historical baseline in z-score units."""
    if threshold <= 0:
        raise ValueError("threshold must be positive")

    rows: list[FeatureDrift] = []
    for feature in FEATURE_COLUMNS:
        if feature not in baseline.columns or feature not in current.columns:
            continue
        base = _numeric(baseline, feature)
        recent = _numeric(current, feature)
        if base.empty or recent.empty:
            continue
        baseline_mean = float(base.mean())
        baseline_std = float(base.std(ddof=0))
        current_mean = float(recent.mean())
        scale = max(baseline_std, 1e-9)
        mean_shift_pct = abs(current_mean - baseline_mean) / max(abs(baseline_mean), 1e-9) * 100.0
        drift_score = abs(current_mean - baseline_mean) / scale
        rows.append(
            FeatureDrift(
                feature=feature,
                baseline_mean=round(baseline_mean, 6),
                current_mean=round(current_mean, 6),
                baseline_std=round(baseline_std, 6),
                mean_shift_pct=round(mean_shift_pct, 2),
                drift_score=round(drift_score, 3),
                drifted=drift_score >= threshold,
            )
        )
    return pd.DataFrame([row.__dict__ for row in rows])


def build_feature_drift_report(
    baseline_frame: pd.DataFrame,
    current_frame: pd.DataFrame,
    *,
    threshold: float = 2.0,
) -> pd.DataFrame:
    """Build a drift report from raw OHLCV frames."""
    baseline_features = build_features(baseline_frame)
    current_features = build_features(current_frame)
    return compare_feature_drift(
        baseline_features,
        current_features,
        threshold=threshold,
    )
