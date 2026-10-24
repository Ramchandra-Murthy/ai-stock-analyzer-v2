"""Tests for the transparent intraday setup scorecard."""

import pandas as pd

from services.intraday_setup_scorecard import build_setup_scorecard, scorecard_frame


def test_scorecard_is_transparent_and_bounded():
    score = build_setup_scorecard(
        {
            "Trend": 1,
            "Volume surge x": 2,
            "VWAP bias": "ABOVE",
            "VWAP": 101,
            "5-min change %": 1,
            "ORB 5m state": "ABOVE",
            "ORB 15m state": "ABOVE",
            "Session phase": "OPEN",
        }
    )
    assert score["Total"] == 100.0
    assert all(0 <= value <= 100 for value in score.values())


def test_scorecard_frame_preserves_rows():
    frame = scorecard_frame(pd.DataFrame([{"Trend": 1, "Volume surge x": 2}]))
    assert len(frame) == 1
    assert "Setup Total" in frame.columns
