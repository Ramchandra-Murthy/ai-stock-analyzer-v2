"""Tests for session-local scan snapshots."""

from datetime import datetime

import pandas as pd

from services.intraday_scan_snapshot import record_scan_snapshot, snapshot_frame


def test_records_scan_snapshot():
    frame = pd.DataFrame(
        [
            {"Symbol": "AAA", "5-min change %": 1.0, "Volume surge x": 2.0},
            {"Symbol": "BBB", "5-min change %": 0.5, "Volume surge x": 1.5},
        ]
    )
    history = record_scan_snapshot(
        [],
        frame,
        datetime.fromisoformat("2026-09-21T12:00:00+05:30"),
    )
    assert history[0]["Candidates"] == 2
    assert history[0]["Average change %"] == 0.75
    assert history[0]["Top symbols"] == "AAA, BBB"


def test_snapshot_frame_has_stable_columns():
    frame = snapshot_frame([])
    assert list(frame.columns) == [
        "Timestamp",
        "Candidates",
        "Average change %",
        "Average volume surge x",
        "Exchanges",
        "Market-cap baskets",
        "Top symbols",
    ]
