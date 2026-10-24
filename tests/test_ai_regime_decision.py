"""Tests for regime-aware AI signal decisions."""

import pytest

from ai_trading.regime_decision import build_regime_aware_decision


def test_bullish_regime_is_included_in_reason() -> None:
    decision = build_regime_aware_decision(
        probability_up=0.80,
        accuracy=0.70,
        roc_auc=0.75,
        trend_score=0.50,
        regime="BULLISH",
        regime_strength=0.80,
    )
    assert decision.signal == "LONG"
    assert "regime BULLISH" in decision.reason


def test_bearish_regime_changes_trend_component() -> None:
    bullish = build_regime_aware_decision(
        probability_up=0.60,
        accuracy=0.70,
        roc_auc=0.70,
        trend_score=0.20,
        regime="BULLISH",
        regime_strength=1.0,
    )
    bearish = build_regime_aware_decision(
        probability_up=0.60,
        accuracy=0.70,
        roc_auc=0.70,
        trend_score=0.20,
        regime="BEARISH",
        regime_strength=1.0,
    )
    assert bullish.trend_pct > bearish.trend_pct


def test_invalid_regime_inputs_are_rejected() -> None:
    with pytest.raises(ValueError):
        build_regime_aware_decision(
            probability_up=0.5,
            accuracy=0.5,
            roc_auc=0.5,
            regime="UNKNOWN",
        )
    with pytest.raises(ValueError):
        build_regime_aware_decision(
            probability_up=0.5,
            accuracy=0.5,
            roc_auc=0.5,
            regime_strength=1.5,
        )
