"""Regime-aware AI signal decision logic."""

from __future__ import annotations

from ai_trading.decision_engine import (
    SignalDecision,
    build_signal_decision,
)

REGIME_ADJUSTMENTS = {
    "BULLISH": 1.0,
    "BEARISH": -1.0,
    "RANGE / MIXED": 0.0,
    "INSUFFICIENT DATA": 0.0,
}


def build_regime_aware_decision(
    *,
    probability_up: float,
    accuracy: float,
    roc_auc: float | None,
    trend_score: float = 0.0,
    calibration_gap: float | None = None,
    regime: str = "INSUFFICIENT DATA",
    regime_strength: float = 0.0,
) -> SignalDecision:
    """Add validated market-regime context to the unified AI decision."""
    if regime not in REGIME_ADJUSTMENTS:
        raise ValueError(f"unsupported regime: {regime}")
    if not 0.0 <= regime_strength <= 1.0:
        raise ValueError("regime_strength must be between 0 and 1")

    regime_score = REGIME_ADJUSTMENTS[regime] * regime_strength
    adjusted_trend = max(-1.0, min(1.0, 0.75 * trend_score + 0.25 * regime_score))
    decision = build_signal_decision(
        probability_up=probability_up,
        accuracy=accuracy,
        roc_auc=roc_auc,
        trend_score=adjusted_trend,
        calibration_gap=calibration_gap,
    )
    return SignalDecision(
        signal=decision.signal,
        confidence_pct=decision.confidence_pct,
        model_confidence_pct=decision.model_confidence_pct,
        validation_pct=decision.validation_pct,
        trend_pct=decision.trend_pct,
        reason=(f"{decision.reason}; regime {regime} " f"(strength {regime_strength:.1%})"),
    )
