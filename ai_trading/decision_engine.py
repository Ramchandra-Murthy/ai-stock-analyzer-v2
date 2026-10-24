"""Unified confidence and decision logic for AI trading signals."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SignalDecision:
    """Unified model decision with transparent component scores."""

    signal: str
    confidence_pct: float
    model_confidence_pct: float
    validation_pct: float
    trend_pct: float
    reason: str


def build_signal_decision(
    *,
    probability_up: float,
    accuracy: float,
    roc_auc: float | None,
    trend_score: float = 0.0,
    calibration_gap: float | None = None,
) -> SignalDecision:
    """Combine ML probability, validation, trend and calibration into one decision."""
    if not 0.0 <= probability_up <= 1.0:
        raise ValueError("probability_up must be between 0 and 1")
    if not 0.0 <= accuracy <= 1.0:
        raise ValueError("accuracy must be between 0 and 1")
    if roc_auc is not None and not 0.0 <= roc_auc <= 1.0:
        raise ValueError("roc_auc must be between 0 and 1")
    if not -1.0 <= trend_score <= 1.0:
        raise ValueError("trend_score must be between -1 and 1")
    if calibration_gap is not None and not 0.0 <= calibration_gap <= 1.0:
        raise ValueError("calibration_gap must be between 0 and 1")

    model_confidence = abs(probability_up - 0.5) * 2.0
    validation = accuracy if roc_auc is None else (accuracy + roc_auc) / 2.0
    if calibration_gap is not None:
        validation *= max(0.0, 1.0 - calibration_gap)

    trend = (trend_score + 1.0) / 2.0
    confidence = 0.50 * model_confidence + 0.30 * validation + 0.20 * abs(trend_score)
    confidence_pct = round(max(0.0, min(1.0, confidence)) * 100.0, 1)

    directional_score = (
        0.65 * (2.0 * probability_up - 1.0) + 0.20 * trend_score + 0.15 * (2.0 * validation - 1.0)
    )
    if confidence_pct < 55.0:
        signal = "NEUTRAL"
    elif directional_score >= 0.15:
        signal = "LONG"
    elif directional_score <= -0.15:
        signal = "SHORT"
    else:
        signal = "NEUTRAL"

    reason = (
        f"ML {probability_up:.1%}; validation {validation:.1%}; "
        f"trend {trend:.1%}; confidence {confidence_pct:.1f}%"
    )
    return SignalDecision(
        signal=signal,
        confidence_pct=confidence_pct,
        model_confidence_pct=round(model_confidence * 100.0, 1),
        validation_pct=round(validation * 100.0, 1),
        trend_pct=round(trend * 100.0, 1),
        reason=reason,
    )
