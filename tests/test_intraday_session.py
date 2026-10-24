"""Tests for intraday Streamlit session lifecycle helpers."""

from services.intraday_session import reset_intraday_session, session_counts


def test_reset_intraday_session_clears_known_keys():
    state = {
        "day_trader_opportunities": [1, 2],
        "intraday_setup_states": {"A": "WATCH"},
        "intraday_setup_monitor": {"A": {}},
        "intraday_setup_outcomes": {"A": {}},
        "intraday_multi_window_outcomes": {"A": {}},
        "intraday_state_transitions": [{"Symbol": "A"}],
        "other": "keep",
    }

    reset_intraday_session(state)

    assert state == {"other": "keep"}


def test_session_counts_are_stable():
    counts = session_counts(
        {
            "day_trader_opportunities": [1, 2],
            "intraday_setup_states": {"A": "WATCH"},
            "intraday_setup_monitor": {},
            "intraday_setup_outcomes": {"A": {}},
            "intraday_state_transitions": [{"Symbol": "A"}],
        }
    )

    assert counts == {
        "Candidates": 2,
        "Setup states": 1,
        "Persisting setups": 0,
        "Outcomes": 1,
        "Transitions": 1,
        "Journal trades": 0,
    }
