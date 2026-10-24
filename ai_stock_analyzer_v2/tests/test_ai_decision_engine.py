"""Tests for the unified AI signal confidence engine."""

import pytest

from ai_trading.decision_engine import build_signal_decision


def test_strong_aligned_signal_gets_high_confidence() -> None:
    decision = build_signal_decision(
        probability_up=0.80,
        accuracy=0.70,
        roc_auc=0.75,
        trend_score=0.80,
    )
    assert decision.signal == "LONG"
    assert decision.confidence_pct > 55.0
    assert decision.validation_pct == pytest.approx(72.5)


def test_low_confidence_signal_becomes_neutral() -> None:
    decision = build_signal_decision(
        probability_up=0.51,
        accuracy=0.50,
        roc_auc=0.50,
        trend_score=0.0,
    )
    assert decision.signal == "NEUTRAL"
    assert decision.confidence_pct < 55.0


def test_calibration_gap_reduces_validation_score() -> None:
    decision = build_signal_decision(
        probability_up=0.80,
        accuracy=0.80,
        roc_auc=0.80,
        trend_score=0.50,
        calibration_gap=0.25,
    )
    assert decision.validation_pct == pytest.approx(60.0)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("probability_up", 1.1),
        ("accuracy", -0.1),
        ("trend_score", 1.1),
    ],
)
def test_invalid_inputs_are_rejected(name: str, value: float) -> None:
    kwargs = {
        "probability_up": 0.5,
        "accuracy": 0.5,
        "roc_auc": 0.5,
        "trend_score": 0.0,
    }
    kwargs[name] = value
    with pytest.raises(ValueError):
        build_signal_decision(**kwargs)
