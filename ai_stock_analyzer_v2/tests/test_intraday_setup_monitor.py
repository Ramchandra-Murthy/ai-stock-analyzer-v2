"""Tests for intraday setup monitoring."""

from datetime import UTC, datetime

import pandas as pd

from services.intraday_setup_monitor import monitor_frame, record_setup_observations


def test_records_observations_and_state_changes():
    observed_at = datetime(2026, 9, 20, 10, 0, tzinfo=UTC)
    results = pd.DataFrame({"Symbol": ["RELIANCE", "TCS"], "Plan state": ["WATCH", "TRIGGERED"]})

    first = record_setup_observations({}, results, observed_at)

    second = record_setup_observations(
        first,
        pd.DataFrame({"Symbol": ["RELIANCE", "TCS"], "Plan state": ["TRIGGERED", "TRIGGERED"]}),
        datetime(2026, 9, 20, 10, 5, tzinfo=UTC),
    )

    assert second["RELIANCE"]["Observations"] == 2
    assert second["RELIANCE"]["State changes"] == 1
    assert second["TCS"]["State changes"] == 0


def test_empty_results_preserve_monitor():
    previous = {"RELIANCE": {"Current state": "WATCH", "Observations": 1}}

    assert record_setup_observations(previous, pd.DataFrame(), datetime.now(UTC)) == previous


def test_monitor_frame_has_stable_columns():
    observed = datetime(2026, 9, 20, 10, 0, tzinfo=UTC)
    monitor = record_setup_observations(
        {},
        pd.DataFrame({"Symbol": ["RELIANCE"], "Plan state": ["WATCH"]}),
        observed,
    )

    frame = monitor_frame(monitor, datetime(2026, 9, 20, 10, 15, tzinfo=UTC))

    assert list(frame.columns) == [
        "Symbol",
        "Current state",
        "Observations",
        "State changes",
        "First observed",
        "Last observed",
        "Current state duration (min)",
    ]
    assert frame.iloc[0]["Current state duration (min)"] == 15.0
