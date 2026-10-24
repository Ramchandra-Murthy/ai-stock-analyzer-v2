from datetime import datetime, timedelta

import pandas as pd

from scanner.eros_regime_history import (
    append_eros_regime_snapshot,
    summarize_eros_regime_history,
)


def _regime(regime: str, rising: float, falling: float, confidence: float) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Signals": 10,
                "Rising Confirmed": 6,
                "Falling Confirmed": 4,
                "Mixed": 0,
                "Insufficient Data": 0,
                "High Confidence": 4,
                "Moderate Confidence": 4,
                "Low Confidence": 2,
                "Rising Breadth %": rising,
                "Falling Breadth %": falling,
                "Average Trend Confidence %": confidence,
                "Regime": regime,
            }
        ]
    )


def test_append_is_bounded_and_deduplicates_timestamp():
    history = None
    for index in range(125):
        history = append_eros_regime_snapshot(
            history,
            datetime(2026, 1, 1, 9, 15) + timedelta(minutes=index),
            _regime("BALANCED", 50.0, 50.0, 60.0),
        )

    assert len(history) == 120
    assert history["Timestamp"].is_monotonic_increasing


def test_summary_detects_regime_transition_and_breadth_change():
    first = append_eros_regime_snapshot(
        None,
        datetime(2026, 1, 1, 9, 15),
        _regime("BALANCED", 50.0, 50.0, 60.0),
    )
    history = append_eros_regime_snapshot(
        first,
        datetime(2026, 1, 1, 9, 20),
        _regime("RISING DOMINANT", 75.0, 25.0, 72.0),
    )

    result = summarize_eros_regime_history(history)
    row = result.iloc[0]

    assert row["Current Regime"] == "RISING DOMINANT"
    assert row["Previous Regime"] == "BALANCED"
    assert row["Regime Transition"] == "BALANCED → RISING DOMINANT"
    assert row["Rising Breadth Δ"] == 25.0
    assert row["Falling Breadth Δ"] == -25.0
    assert row["Snapshots"] == 2


def test_invalid_input_returns_empty():
    assert summarize_eros_regime_history(None).empty
    assert summarize_eros_regime_history(pd.DataFrame()).empty
    assert append_eros_regime_snapshot(
        None, datetime(2026, 1, 1, 9, 15), pd.DataFrame({"Regime": ["BALANCED"]})
    ).empty
