"""Tests for intraday scan health history helpers."""

from datetime import UTC, datetime

import pandas as pd

from services.intraday_health_history import (
    health_history_frame,
    record_health_observation,
)


def test_records_latest_health_first():
    observed_at = datetime(2026, 9, 21, 9, 30, tzinfo=UTC)
    history = [{"Status": "STALE", "Observed at": observed_at}]

    updated = record_health_observation(
        history,
        {"status": "HEALTHY", "message": "Fresh", "candidates": 4},
        datetime(2026, 9, 21, 9, 35, tzinfo=UTC),
    )

    assert updated[0]["Status"] == "HEALTHY"
    assert updated[1]["Status"] == "STALE"


def test_health_history_frame_has_stable_columns():
    frame = health_history_frame(
        [
            {
                "Observed at": datetime(2026, 9, 21, 9, 30, tzinfo=UTC),
                "Status": "HEALTHY",
                "Message": "Fresh",
                "Age minutes": 1.2,
                "Candidates": 3,
            }
        ]
    )

    assert list(frame.columns) == [
        "Observed at",
        "Status",
        "Message",
        "Age minutes",
        "Candidates",
    ]
    assert isinstance(frame, pd.DataFrame)


def test_empty_health_history_has_stable_columns():
    frame = health_history_frame([])

    assert frame.empty
    assert list(frame.columns) == [
        "Observed at",
        "Status",
        "Message",
        "Age minutes",
        "Candidates",
    ]
