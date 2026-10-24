from datetime import UTC, datetime

import pandas as pd

from scanner.institutional_momentum_history import append_momentum_snapshot


def test_append_momentum_snapshot_creates_history():
    result = append_momentum_snapshot(
        None,
        datetime(2026, 9, 18, 10, tzinfo=UTC),
        62.5,
        "POSITIVE",
    )
    assert len(result) == 1
    assert result.iloc[0]["Score"] == 62.5
    assert result.iloc[0]["Label"] == "POSITIVE"


def test_append_momentum_snapshot_replaces_duplicate_timestamp():
    timestamp = datetime(2026, 9, 18, 10, tzinfo=UTC)
    history = pd.DataFrame([{"Timestamp": timestamp, "Score": 55.0, "Label": "NEUTRAL"}])
    result = append_momentum_snapshot(history, timestamp, 70.0, "POSITIVE")
    assert len(result) == 1
    assert result.iloc[0]["Score"] == 70.0
    assert result.iloc[0]["Label"] == "POSITIVE"


def test_append_momentum_snapshot_keeps_latest_300_rows():
    history = pd.DataFrame(
        {
            "Timestamp": pd.date_range("2026-01-01", periods=300, freq="min"),
            "Score": range(300),
            "Label": ["NEUTRAL"] * 300,
        }
    )
    result = append_momentum_snapshot(
        history,
        datetime(2026, 1, 1, 5, 0),
        75.0,
        "STRONG POSITIVE",
    )
    assert len(result) == 300
    assert result.iloc[-1]["Score"] == 75.0
