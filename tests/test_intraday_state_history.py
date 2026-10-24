"""Tests for intraday setup state transition history."""

from datetime import UTC, datetime

import pandas as pd

from services.intraday_state_history import (
    record_setup_state_transitions,
    transitions_frame,
)


def test_records_only_changed_states():
    previous = {"RELIANCE": "WAITING FOR REFERENCE", "TCS": "INVALIDATED"}
    results = pd.DataFrame(
        {
            "Symbol": ["RELIANCE", "TCS", "INFY"],
            "Plan state": [
                "TRIGGERED / ABOVE REFERENCE",
                "INVALIDATED",
                "WAITING FOR REFERENCE",
            ],
        }
    )

    updated, transitions = record_setup_state_transitions(
        previous,
        results,
        datetime(2026, 9, 20, 10, 15, tzinfo=UTC),
    )

    assert updated["RELIANCE"] == "TRIGGERED / ABOVE REFERENCE"
    assert updated["TCS"] == "INVALIDATED"
    assert updated["INFY"] == "WAITING FOR REFERENCE"
    assert len(transitions) == 1
    assert transitions[0]["Symbol"] == "RELIANCE"


def test_empty_results_do_not_create_transitions():
    previous = {"RELIANCE": "WAITING FOR REFERENCE"}

    updated, transitions = record_setup_state_transitions(
        previous,
        pd.DataFrame(),
        datetime.now(UTC),
    )

    assert updated == previous
    assert transitions == []


def test_transitions_frame_has_stable_columns():
    frame = transitions_frame(
        [
            {
                "Observed at": datetime(2026, 9, 20, 10, 15),
                "Symbol": "RELIANCE",
                "Previous state": "WAITING FOR REFERENCE",
                "New state": "TRIGGERED / ABOVE REFERENCE",
            }
        ]
    )

    assert list(frame.columns) == [
        "Observed at",
        "Symbol",
        "Previous state",
        "New state",
    ]
    assert frame.iloc[0]["Symbol"] == "RELIANCE"
