import pandas as pd
import pytest

from ai_trading.adaptive_engine import (
    apply_adaptive_confidence,
    build_adaptive_adjustments,
)


def _history() -> pd.DataFrame:
    rows = []
    for index in range(10):
        rows.append(
            {
                "signal": "LONG",
                "regime": "BULLISH",
                "completed": True,
                "return_pct": 2.0 if index < 8 else -1.0,
                "confidence_pct": 70.0,
            }
        )
    rows.append(
        {
            "signal": "SHORT",
            "regime": "BEARISH",
            "completed": False,
            "return_pct": None,
            "confidence_pct": 80.0,
        }
    )
    return pd.DataFrame(rows)


def test_adaptive_adjustment_is_bounded_and_uses_completed_outcomes() -> None:
    adjustments = build_adaptive_adjustments(
        _history(),
        min_samples=10,
        max_adjustment_pct=10.0,
    )

    row = adjustments.iloc[0]
    assert row["samples"] == 10
    assert row["observed_win_rate_pct"] == pytest.approx(80.0)
    assert row["average_confidence_pct"] == pytest.approx(70.0)
    assert row["adjustment_pct"] == pytest.approx(10.0)


def test_small_samples_are_ignored() -> None:
    history = _history().iloc[:9]
    adjustments = build_adaptive_adjustments(history, min_samples=10)
    assert adjustments.empty


def test_adaptive_confidence_uses_exact_regime_match() -> None:
    adjustments = build_adaptive_adjustments(_history(), min_samples=10)

    adjusted = apply_adaptive_confidence(
        70.0,
        signal="LONG",
        regime="BULLISH",
        adjustments=adjustments,
    )
    assert adjusted == pytest.approx(80.0)


def test_no_matching_adjustment_preserves_confidence() -> None:
    adjustments = build_adaptive_adjustments(_history(), min_samples=10)

    adjusted = apply_adaptive_confidence(
        60.0,
        signal="SHORT",
        regime="BEARISH",
        adjustments=adjustments,
    )
    assert adjusted == pytest.approx(60.0)


def test_confidence_validation() -> None:
    with pytest.raises(ValueError):
        apply_adaptive_confidence(-1.0, signal="LONG")

    with pytest.raises(ValueError):
        build_adaptive_adjustments(_history(), min_samples=0)
