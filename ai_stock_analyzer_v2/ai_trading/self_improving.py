"""Leakage-safe model retraining readiness analytics."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class RetrainingDecision:
    """Historical evidence used to decide whether retraining is due."""

    should_retrain: bool
    reason: str
    completed_samples: int
    recent_win_rate_pct: float
    recent_avg_return_pct: float
    recent_avg_confidence_pct: float


def evaluate_retraining_need(
    history: pd.DataFrame,
    *,
    min_samples: int = 30,
    lookback: int = 30,
    min_win_rate_pct: float = 50.0,
    max_confidence_gap_pct: float = 15.0,
) -> RetrainingDecision:
    """Evaluate retraining readiness using only completed historical outcomes."""
    if min_samples < 1 or lookback < 1:
        raise ValueError("min_samples and lookback must be at least 1")
    if not 0.0 <= min_win_rate_pct <= 100.0:
        raise ValueError("min_win_rate_pct must be between 0 and 100")
    if max_confidence_gap_pct < 0.0:
        raise ValueError("max_confidence_gap_pct must be non-negative")

    empty = RetrainingDecision(False, "INSUFFICIENT DATA", 0, 0.0, 0.0, 0.0)
    if history.empty or not {"completed", "return_pct", "confidence_pct"}.issubset(history.columns):
        return empty

    completed = history[history["completed"]].copy()
    completed["return_pct"] = pd.to_numeric(completed["return_pct"], errors="coerce")
    completed["confidence_pct"] = pd.to_numeric(completed["confidence_pct"], errors="coerce")
    completed = completed.dropna(subset=["return_pct", "confidence_pct"])
    if len(completed) < min_samples:
        return empty.__class__(False, "INSUFFICIENT SAMPLES", len(completed), 0.0, 0.0, 0.0)

    recent = completed.tail(lookback)
    win_rate = float((recent["return_pct"] > 0.0).mean() * 100.0)
    avg_return = float(recent["return_pct"].mean())
    avg_confidence = float(recent["confidence_pct"].mean())
    gap = avg_confidence - win_rate
    should = win_rate < min_win_rate_pct or gap > max_confidence_gap_pct
    reason = "RETRAIN DUE" if should else "MODEL STABLE"
    return RetrainingDecision(
        should,
        reason,
        len(completed),
        round(win_rate, 2),
        round(avg_return, 2),
        round(avg_confidence, 2),
    )
