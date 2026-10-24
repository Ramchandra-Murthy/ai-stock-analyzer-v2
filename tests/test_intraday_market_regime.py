"""Tests for descriptive intraday market-regime metrics."""

from datetime import datetime, timedelta

import pandas as pd

from services.intraday_market_regime import classify_market_regime


def _frame() -> pd.DataFrame:
    start = datetime.fromisoformat("2026-09-21T09:15:00+05:30")
    return pd.DataFrame(
        {
            "Close": [100, 100.2, 100.4, 100.8, 101.2],
            "High": [100.3, 100.5, 100.7, 101.1, 101.5],
            "Low": [99.8, 100.0, 100.2, 100.5, 100.9],
            "Volume": [1000, 1000, 1000, 1000, 2000],
        },
        index=[start + timedelta(minutes=5 * i) for i in range(5)],
    )


def test_classifies_observed_trend_and_volume():
    result = classify_market_regime(_frame())
    assert result["Trend regime"] == "TRENDING UP"
    assert result["Volume regime"] == "ELEVATED"


def test_empty_frame_returns_empty_metrics():
    assert classify_market_regime(pd.DataFrame()) == {}
