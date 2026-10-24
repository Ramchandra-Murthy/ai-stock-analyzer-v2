"""Tests for descriptive intraday alert detection."""

from datetime import datetime

import pandas as pd

from services.intraday_alert_engine import (
    alert_history_frame,
    append_alert_history,
    detect_intraday_alerts,
)


def _frame(price_change: float, volume: float, score: float, state: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Symbol": "TEST",
                "Exchange": "NSE",
                "5-min change %": price_change,
                "Volume surge x": volume,
                "Composite score": score,
                "Plan state": state,
            }
        ]
    )


def test_detects_new_candidate():
    alerts = detect_intraday_alerts(
        None,
        _frame(1.2, 1.5, 60, "WATCH"),
        datetime.fromisoformat("2026-09-21T12:00:00+05:30"),
    )

    assert [alert["Alert"] for alert in alerts] == ["NEW_CANDIDATE"]


def test_detects_price_volume_score_and_state_changes():
    alerts = detect_intraday_alerts(
        _frame(0.5, 1.0, 40, "WATCH"),
        _frame(2.0, 1.8, 55, "BREAKOUT"),
        datetime.fromisoformat("2026-09-21T12:05:00+05:30"),
    )

    assert {alert["Alert"] for alert in alerts} == {
        "PRICE_CHANGE",
        "VOLUME_CHANGE",
        "SCORE_CHANGE",
        "STATE_CHANGE",
    }


def test_tracks_candidate_removal_and_history_limit():
    alerts = detect_intraday_alerts(
        _frame(1.0, 1.0, 50, "WATCH"),
        pd.DataFrame(columns=["Symbol", "Exchange"]),
        datetime.fromisoformat("2026-09-21T12:10:00+05:30"),
    )
    history = append_alert_history([], alerts, limit=1)

    assert len(history) == 1
    assert history[0]["Alert"] == "REMOVED_CANDIDATE"
    assert list(alert_history_frame(history).columns) == [
        "Timestamp",
        "Symbol",
        "Exchange",
        "Alert",
        "Message",
    ]
