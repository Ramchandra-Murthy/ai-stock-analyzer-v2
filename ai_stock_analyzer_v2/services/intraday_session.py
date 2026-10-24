"""Helpers for managing the intraday Streamlit session lifecycle."""

from __future__ import annotations

from typing import Any

SESSION_KEYS = (
    "day_trader_opportunities",
    "intraday_setup_states",
    "intraday_setup_monitor",
    "intraday_setup_outcomes",
    "intraday_multi_window_outcomes",
    "intraday_state_transitions",
    "intraday_alert_history",
    "intraday_trade_journal",
)


def reset_intraday_session(session_state: dict[str, Any]) -> None:
    """Clear stored intraday scan and observation history."""
    for key in SESSION_KEYS:
        session_state.pop(key, None)


def session_counts(session_state: dict[str, Any]) -> dict[str, int]:
    """Return stable counts for the current intraday session."""
    return {
        "Candidates": _size(session_state.get("day_trader_opportunities")),
        "Setup states": _size(session_state.get("intraday_setup_states")),
        "Persisting setups": _size(session_state.get("intraday_setup_monitor")),
        "Outcomes": _size(session_state.get("intraday_setup_outcomes")),
        "Transitions": _size(session_state.get("intraday_state_transitions")),
        "Journal trades": _size(session_state.get("intraday_trade_journal")),
    }


def _size(value: Any) -> int:
    """Return a safe size for common session-state containers."""
    if value is None:
        return 0
    try:
        return len(value)
    except TypeError:
        return 0
