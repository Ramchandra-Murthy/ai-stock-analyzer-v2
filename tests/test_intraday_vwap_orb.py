"""Tests for VWAP and opening-range metrics."""

from datetime import datetime, timedelta

import pandas as pd

from services.intraday_vwap_orb import vwap_orb_metrics


def _bars() -> pd.DataFrame:
    start = datetime.fromisoformat("2026-09-21T09:15:00+05:30")
    rows = []
    for index in range(4):
        rows.append(
            {
                "Open": 100 + index,
                "High": 102 + index,
                "Low": 99 + index,
                "Close": 101 + index,
                "Volume": 1000,
            }
        )
    frame = pd.DataFrame(rows)
    frame.index = [start + timedelta(minutes=5 * i) for i in range(4)]
    return frame


def test_calculates_vwap_and_five_minute_orb():
    metrics = vwap_orb_metrics(_bars(), orb_minutes=(5, 15))
    assert metrics["VWAP"] == 102.17
    assert metrics["VWAP bias"] == "ABOVE"
    assert metrics["ORB 5m high"] == 102
    assert metrics["ORB 5m low"] == 99


def test_fifteen_minute_orb_uses_three_five_minute_bars():
    metrics = vwap_orb_metrics(_bars(), orb_minutes=(15,))
    assert metrics["ORB 15m high"] == 104
    assert metrics["ORB 15m low"] == 99
