"""Tests for consolidated intraday signal validation."""

from datetime import UTC, datetime

import pandas as pd

from services.intraday_signal_validation import (
    build_signal_validation_frame,
    validation_summary,
)


def test_builds_validation_frame_from_observed_outcomes():
    observed = datetime(2026, 9, 25, 10, 0, tzinfo=UTC)
    outcomes = {
        "RELIANCE": {
            "Symbol": "RELIANCE",
            "State": "TRIGGERED",
            "First price": 100.0,
            "Current price": 102.0,
            "Price change %": 2.0,
            "First observed": observed,
            "Last observed": observed,
            "Observations": 3,
        },
        "TCS": {
            "Symbol": "TCS",
            "State": "WATCH",
            "First price": 200.0,
            "Current price": 199.0,
            "Price change %": -0.5,
            "First observed": observed,
            "Last observed": observed,
            "Observations": 2,
        },
    }
    windows = {
        "RELIANCE": {
            "Symbol": "RELIANCE",
            "State": "TRIGGERED",
            "5m change %": 0.8,
            "10m change %": 1.2,
            "15m change %": None,
            "30m change %": None,
        }
    }
    results = pd.DataFrame(
        {
            "Symbol": ["RELIANCE", "TCS"],
            "Exchange": ["NSE", "NSE"],
            "Direction": ["LONG", "SHORT"],
            "Day-trading setup": ["BREAKOUT", "VWAP"],
        }
    )

    frame = build_signal_validation_frame(outcomes, windows, results)

    assert list(frame["Symbol"]) == ["TCS", "RELIANCE"]
    assert set(frame["Outcome"]) == {"Positive", "Negative"}
    reliance = frame.loc[frame["Symbol"] == "RELIANCE"].iloc[0]
    assert reliance["5m change %"] == 0.8
    assert reliance["Direction"] == "LONG"


def test_validation_summary_counts_outcomes():
    validation = pd.DataFrame({"Outcome": ["Positive", "Negative", "Flat", "Unresolved"]})
    summary = validation_summary(validation)
    values = dict(zip(summary["Metric"], summary["Value"], strict=True))

    assert values["Positive"] == 1
    assert values["Negative"] == 1
    assert values["Flat"] == 1
    assert values["Unresolved"] == 1
    assert values["Tracked setups"] == 4
