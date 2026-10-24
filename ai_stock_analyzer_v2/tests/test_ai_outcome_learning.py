import pandas as pd
import pytest

from ai_trading.outcome_learning import (
    confidence_bucket,
    confidence_learning_summary,
    outcome_learning_summary,
    regime_learning_summary,
)


def _history() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "signal": "LONG",
                "regime": "BULLISH",
                "completed": True,
                "return_pct": 10.0,
                "confidence_pct": 80.0,
            },
            {
                "signal": "LONG",
                "regime": "BULLISH",
                "completed": True,
                "return_pct": -5.0,
                "confidence_pct": 70.0,
            },
            {
                "signal": "SHORT",
                "regime": "BEARISH",
                "completed": True,
                "return_pct": 4.0,
                "confidence_pct": 60.0,
            },
            {
                "signal": "SHORT",
                "regime": "BEARISH",
                "completed": False,
                "return_pct": None,
                "confidence_pct": 90.0,
            },
        ]
    )


def test_confidence_bucket_boundaries():
    assert confidence_bucket(54.9) == "<55%"
    assert confidence_bucket(55.0) == "55-65%"
    assert confidence_bucket(65.0) == "65-75%"
    assert confidence_bucket(75.0) == "75%+"


def test_outcome_learning_summary_by_signal():
    summary = outcome_learning_summary(_history(), group_by="signal")
    long_row = summary[summary["group"] == "LONG"].iloc[0]

    assert long_row["signals"] == 2
    assert long_row["wins"] == 1
    assert long_row["win_rate_pct"] == pytest.approx(50.0)
    assert long_row["avg_return_pct"] == pytest.approx(2.5)
    assert long_row["avg_confidence_pct"] == pytest.approx(75.0)
    assert long_row["confidence_gap_pct"] == pytest.approx(25.0)


def test_confidence_learning_uses_completed_signals_only():
    summary = confidence_learning_summary(_history())

    assert summary["signals"].sum() == 3
    assert "75%+" in set(summary["group"])


def test_regime_learning_summary():
    summary = regime_learning_summary(_history())
    bullish = summary[summary["group"] == "BULLISH"].iloc[0]

    assert bullish["signals"] == 2
    assert bullish["win_rate_pct"] == pytest.approx(50.0)


def test_missing_regime_returns_empty_summary():
    history = _history().drop(columns=["regime"])
    assert regime_learning_summary(history).empty
