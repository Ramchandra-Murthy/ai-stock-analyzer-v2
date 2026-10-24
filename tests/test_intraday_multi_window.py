"""Tests for multi-window intraday setup outcomes."""

from datetime import UTC, datetime

import pandas as pd

from services.intraday_multi_window import (
    multi_window_frame,
    record_multi_window_outcomes,
)


def test_fills_elapsed_windows():
    first = datetime(2026, 9, 20, 10, 0, tzinfo=UTC)
    tenth = datetime(2026, 9, 20, 10, 10, tzinfo=UTC)
    start = pd.DataFrame({"Symbol": ["RELIANCE"], "Plan state": ["TRIGGERED"], "Price": [100.0]})
    later = pd.DataFrame({"Symbol": ["RELIANCE"], "Plan state": ["TRIGGERED"], "Price": [102.0]})

    tracked = record_multi_window_outcomes({}, start, first)
    tracked = record_multi_window_outcomes(tracked, later, tenth)

    assert tracked["RELIANCE"]["5m change %"] == 2.0
    assert tracked["RELIANCE"]["10m change %"] == 2.0
    assert tracked["RELIANCE"]["15m change %"] is None
    assert tracked["RELIANCE"]["30m change %"] is None


def test_state_change_resets_all_windows():
    observed = datetime(2026, 9, 20, 10, 10, tzinfo=UTC)
    tracked = record_multi_window_outcomes(
        {},
        pd.DataFrame({"Symbol": ["TCS"], "Plan state": ["WATCH"], "Price": [200.0]}),
        observed,
    )
    updated = record_multi_window_outcomes(
        tracked,
        pd.DataFrame({"Symbol": ["TCS"], "Plan state": ["TRIGGERED"], "Price": [210.0]}),
        observed,
    )

    assert updated["TCS"]["Baseline price"] == 210.0
    assert updated["TCS"]["5m change %"] is None


def test_empty_frame_has_stable_columns():
    frame = multi_window_frame({})

    assert list(frame.columns) == [
        "Symbol",
        "State",
        "Baseline price",
        "5m change %",
        "10m change %",
        "15m change %",
        "30m change %",
        "Observations",
    ]
