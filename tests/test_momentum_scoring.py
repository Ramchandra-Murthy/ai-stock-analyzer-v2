"""Tests for the standalone momentum scoring engine."""

import pytest

from ai_trading.momentum_scoring import DEFAULT_WEIGHTS, score_momentum


def test_score_is_weighted_and_bounded() -> None:
    result = score_momentum(
        {
            "trend": 80,
            "relative_strength": 60,
            "volume_expansion": 100,
            "breakout_quality": 40,
        }
    )
    expected = (
        80 * DEFAULT_WEIGHTS["trend"]
        + 60 * DEFAULT_WEIGHTS["relative_strength"]
        + 100 * DEFAULT_WEIGHTS["volume_expansion"]
        + 40 * DEFAULT_WEIGHTS["breakout_quality"]
    )
    assert result.score == pytest.approx(expected)
    assert 0 <= result.score <= 100


def test_missing_components_renormalize_remaining_weights() -> None:
    result = score_momentum({"trend": 80, "relative_strength": None})
    assert result.score == 80
    assert result.components["relative_strength"] is None


def test_custom_weights_are_supported() -> None:
    result = score_momentum(
        {"trend": 100, "relative_strength": 0},
        weights={
            "trend": 3,
            "relative_strength": 1,
            "volume_expansion": 0,
            "breakout_quality": 0,
        },
    )
    assert result.score == 75


def test_no_valid_weighted_components_returns_none() -> None:
    result = score_momentum({"trend": None})
    assert result.score is None
    assert "unavailable" in result.explanation.lower()


@pytest.mark.parametrize("value", [-1, 101, float("nan"), float("inf")])
def test_invalid_component_values_are_rejected(value: float) -> None:
    with pytest.raises(ValueError):
        score_momentum({"trend": value})


def test_unknown_component_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown"):
        score_momentum({"trend": 50, "momentum": 80})


def test_invalid_weights_are_rejected() -> None:
    with pytest.raises(ValueError):
        score_momentum(
            {"trend": 50},
            weights={
                "trend": -1,
                "relative_strength": 0,
                "volume_expansion": 0,
                "breakout_quality": 0,
            },
        )


def test_explanation_identifies_component_strengths() -> None:
    result = score_momentum(
        {"trend": 90, "relative_strength": 30, "volume_expansion": 50, "breakout_quality": 60}
    )
    assert "strongest: trend" in result.explanation
    assert "weakest: relative strength" in result.explanation
