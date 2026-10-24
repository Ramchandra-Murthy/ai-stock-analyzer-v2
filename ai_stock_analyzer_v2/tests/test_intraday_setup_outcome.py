"""Tests for intraday setup outcome tracking."""

from datetime import UTC, datetime

import pandas as pd

from services.intraday_setup_outcome import outcomes_frame, record_setup_outcomes


def test_records_price_change_for_same_setup_state():
    first_time = datetime(2026, 9, 20, 10, 0, tzinfo=UTC)
    second_time = datetime(2026, 9, 20, 10, 5, tzinfo=UTC)
    results = pd.DataFrame({"Symbol": ["RELIANCE"], "Plan state": ["TRIGGERED"], "Price": [100.0]})

    first = record_setup_outcomes({}, results, first_time)
    second = record_setup_outcomes(
        first,
        pd.DataFrame({"Symbol": ["RELIANCE"], "Plan state": ["TRIGGERED"], "Price": [102.0]}),
        second_time,
    )

    assert second["RELIANCE"]["First price"] == 100.0
    assert second["RELIANCE"]["Current price"] == 102.0
    assert second["RELIANCE"]["Price change %"] == 2.0
    assert second["RELIANCE"]["Observations"] == 2


def test_new_state_resets_outcome_baseline():
    observed = datetime(2026, 9, 20, 10, 5, tzinfo=UTC)
    previous = record_setup_outcomes(
        {},
        pd.DataFrame({"Symbol": ["TCS"], "Plan state": ["WATCH"], "Price": [200.0]}),
        observed,
    )

    updated = record_setup_outcomes(
        previous,
        pd.DataFrame({"Symbol": ["TCS"], "Plan state": ["TRIGGERED"], "Price": [210.0]}),
        observed,
    )

    assert updated["TCS"]["First price"] == 210.0
    assert updated["TCS"]["Price change %"] == 0.0


def test_empty_outcomes_frame_has_stable_columns():
    frame = outcomes_frame({})

    assert list(frame.columns) == [
        "Symbol",
        "State",
        "First price",
        "Current price",
        "Price change %",
        "First observed",
        "Last observed",
        "Observations",
    ]
