"""Tests for intraday setup session-phase analysis."""

from datetime import UTC, datetime

from services.intraday_setup_regime import regime_statistics, session_phase


def test_session_phase_boundaries():
    assert session_phase(datetime(2026, 9, 20, 4, 0, tzinfo=UTC)) == "Opening (09:15-10:00)"
    assert session_phase(datetime(2026, 9, 20, 4, 30, tzinfo=UTC)) == "Morning (10:00-12:00)"


def test_regime_statistics_groups_state_and_phase():
    outcomes = {
        "A": {
            "State": "TRIGGERED",
            "Price change %": 2.0,
            "First observed": datetime(2026, 9, 20, 4, 0, tzinfo=UTC),
        },
        "B": {
            "State": "TRIGGERED",
            "Price change %": -1.0,
            "First observed": datetime(2026, 9, 20, 4, 5, tzinfo=UTC),
        },
    }

    frame = regime_statistics(outcomes)

    assert len(frame) == 1
    assert frame.iloc[0]["State"] == "TRIGGERED"
    assert frame.iloc[0]["Setups"] == 2
    assert frame.iloc[0]["Positive rate %"] == 50.0


def test_empty_regime_statistics_has_stable_columns():
    assert list(regime_statistics({}).columns) == [
        "Session phase",
        "State",
        "Setups",
        "Positive outcomes",
        "Negative outcomes",
        "Positive rate %",
        "Average change %",
    ]
