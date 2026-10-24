"""Tests for intraday dashboard health checks."""

from datetime import UTC, datetime, timedelta

import pandas as pd

from services.intraday_health import assess_scan_health


def test_no_scan_is_reported():
    result = assess_scan_health(None, None)
    assert result["status"] == "NO_SCAN"


def test_missing_required_columns_is_reported():
    result = assess_scan_health(
        pd.DataFrame({"Symbol": ["RELIANCE"]}),
        datetime.now(UTC),
    )
    assert result["status"] == "INVALID_SCHEMA"


def test_stale_scan_is_reported():
    observed_at = datetime.now(UTC) - timedelta(minutes=15)
    result = assess_scan_health(
        pd.DataFrame({"Symbol": ["RELIANCE"], "Price": [2500.0]}),
        observed_at,
        max_age_minutes=10,
    )
    assert result["status"] == "STALE"


def test_fresh_scan_is_healthy():
    result = assess_scan_health(
        pd.DataFrame({"Symbol": ["RELIANCE"], "Price": [2500.0]}),
        datetime.now(UTC),
    )
    assert result["status"] == "HEALTHY"
    assert result["candidates"] == 1
