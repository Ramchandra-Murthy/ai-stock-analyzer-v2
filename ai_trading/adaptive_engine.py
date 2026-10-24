"""Leakage-safe adaptive confidence adjustments from completed signal outcomes."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ai_trading.outcome_learning import confidence_bucket


@dataclass(frozen=True)
class AdaptiveAdjustment:
    """Historical calibration adjustment for one signal/regime segment."""

    signal: str
    regime: str
    confidence_bucket: str
    samples: int
    observed_win_rate_pct: float
    average_confidence_pct: float
    adjustment_pct: float


def build_adaptive_adjustments(
    history: pd.DataFrame,
    *,
    min_samples: int = 10,
    max_adjustment_pct: float = 10.0,
) -> pd.DataFrame:
    """Learn bounded confidence adjustments from completed historical outcomes.

    Only completed outcomes are used. Segments below the minimum sample count
    are excluded to reduce overfitting to small samples.
    """
    if min_samples < 1:
        raise ValueError("min_samples must be at least 1")
    if max_adjustment_pct <= 0.0:
        raise ValueError("max_adjustment_pct must be positive")

    columns = [
        "signal",
        "regime",
        "confidence_bucket",
        "samples",
        "observed_win_rate_pct",
        "average_confidence_pct",
        "adjustment_pct",
    ]
    required = {"completed", "return_pct", "confidence_pct", "signal"}
    if history.empty or not required.issubset(history.columns):
        return pd.DataFrame(columns=columns)

    completed = history[history["completed"]].copy()
    completed["return_pct"] = pd.to_numeric(completed["return_pct"], errors="coerce")
    completed["confidence_pct"] = pd.to_numeric(completed["confidence_pct"], errors="coerce")
    completed = completed.dropna(subset=["return_pct", "confidence_pct", "signal"])
    if completed.empty:
        return pd.DataFrame(columns=columns)

    if "regime" not in completed.columns:
        completed["regime"] = "ALL"
    completed["regime"] = completed["regime"].fillna("ALL").astype(str)
    completed["confidence_bucket"] = completed["confidence_pct"].map(
        lambda value: confidence_bucket(float(value))
    )
    completed["win"] = completed["return_pct"] > 0.0

    summary = completed.groupby(
        ["signal", "regime", "confidence_bucket"],
        as_index=False,
    ).agg(
        samples=("win", "size"),
        observed_win_rate_pct=("win", "mean"),
        average_confidence_pct=("confidence_pct", "mean"),
    )
    summary = summary[summary["samples"] >= min_samples].copy()
    if summary.empty:
        return pd.DataFrame(columns=columns)

    summary["observed_win_rate_pct"] *= 100.0
    summary["adjustment_pct"] = (
        summary["observed_win_rate_pct"] - summary["average_confidence_pct"]
    ).clip(-max_adjustment_pct, max_adjustment_pct)
    numeric = [
        "observed_win_rate_pct",
        "average_confidence_pct",
        "adjustment_pct",
    ]
    summary[numeric] = summary[numeric].round(2)
    return (
        summary[columns]
        .sort_values(["signal", "regime", "confidence_bucket"])
        .reset_index(drop=True)
    )


def apply_adaptive_confidence(
    confidence_pct: float,
    *,
    signal: str,
    regime: str = "ALL",
    adjustments: pd.DataFrame | None = None,
) -> float:
    """Apply a learned adjustment without changing the signal direction."""
    if not 0.0 <= confidence_pct <= 100.0:
        raise ValueError("confidence_pct must be between 0 and 100")
    if adjustments is None or adjustments.empty:
        return round(confidence_pct, 1)

    bucket = confidence_bucket(confidence_pct)
    exact = adjustments[
        (adjustments["signal"] == signal)
        & (adjustments["regime"] == regime)
        & (adjustments["confidence_bucket"] == bucket)
    ]
    fallback = adjustments[
        (adjustments["signal"] == signal)
        & (adjustments["regime"] == "ALL")
        & (adjustments["confidence_bucket"] == bucket)
    ]
    matches = exact if not exact.empty else fallback
    if matches.empty:
        return round(confidence_pct, 1)

    adjustment = float(matches.iloc[0]["adjustment_pct"])
    return round(max(0.0, min(100.0, confidence_pct + adjustment)), 1)
