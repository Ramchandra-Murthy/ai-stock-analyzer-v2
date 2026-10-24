"""Tests for adaptive AI signal performance analytics."""

import pandas as pd
import pytest

from ai_trading.adaptive_performance import (
    adaptive_confidence_bucket_summary,
    adaptive_effect_summary,
    adaptive_performance_summary,
)


def _history() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "signal": "LONG",
                "regime": "BULLISH",
                "completed": True,
                "return_pct": 2.0,
                "confidence_pct": 60.0,
                "adaptive_confidence_pct": 65.0,
            },
            {
                "signal": "LONG",
                "regime": "BULLISH",
                "completed": True,
                "return_pct": -1.0,
                "confidence_pct": 60.0,
                "adaptive_confidence_pct": 62.0,
            },
            {
                "signal": "SHORT",
                "regime": "BEARISH",
                "completed": True,
                "return_pct": 1.5,
                "confidence_pct": 75.0,
                "adaptive_confidence_pct": 70.0,
            },
            {
                "signal": "LONG",
                "regime": "BULLISH",
                "completed": False,
                "return_pct": None,
                "confidence_pct": 60.0,
                "adaptive_confidence_pct": 65.0,
            },
        ]
    )


def test_adaptive_performance_uses_completed_rows_only() -> None:
    summary = adaptive_performance_summary(_history())
    long_row = summary[summary["group"] == "LONG"].iloc[0]

    assert long_row["signals"] == 2
    assert long_row["wins"] == 1
    assert long_row["win_rate_pct"] == pytest.approx(50.0)
    assert long_row["avg_adaptive_adjustment_pct"] == pytest.approx(3.5)


def test_adaptive_bucket_summary_groups_realized_results() -> None:
    summary = adaptive_confidence_bucket_summary(_history())
    assert not summary.empty
    assert set(summary["group"]) == {"55-65%", "65-75%"}


def test_adaptive_effect_summary_reports_raw_vs_adaptive() -> None:
    result = adaptive_effect_summary(_history())

    assert result["completed"] == 3.0
    assert result["average_raw_confidence_pct"] == pytest.approx(65.0)
    assert result["average_adaptive_confidence_pct"] == pytest.approx(65.67, abs=0.01)
    assert result["average_adjustment_pct"] == pytest.approx(0.67, abs=0.01)
    assert result["win_rate_pct"] == pytest.approx(66.67, abs=0.01)


def test_missing_adaptive_columns_return_empty_summary() -> None:
    history = _history().drop(columns=["adaptive_confidence_pct"])
    assert adaptive_performance_summary(history).empty
