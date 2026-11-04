"""Tests for the intraday momentum radar feature engine."""

import pandas as pd
import pytest

from scanner.intraday_momentum import (
    RadarConfig,
    build_intraday_radar_features,
)


def _bars(times, *, opens, highs, lows, closes, volumes):
    index = pd.to_datetime(times).tz_localize("Asia/Kolkata")
    return pd.DataFrame(
        {
            "Open": opens,
            "High": highs,
            "Low": lows,
            "Close": closes,
            "Volume": volumes,
        },
        index=index,
    )


def test_empty_input_returns_no_data():
    result = build_intraday_radar_features(pd.DataFrame())
    assert result["status"] == "NO_DATA"
    assert result["score"] == 0


def test_missing_ohlcv_column_is_rejected():
    with pytest.raises(ValueError, match="Missing OHLCV"):
        build_intraday_radar_features(pd.DataFrame({"Close": [10]}))


def test_features_include_vwap_opening_range_and_percent_change():
    bars = _bars(
        ["2026-11-04 09:15", "2026-11-04 09:20", "2026-11-04 09:30", "2026-11-04 09:35"],
        opens=[100, 102, 104, 106],
        highs=[102, 104, 106, 109],
        lows=[99, 101, 103, 105],
        closes=[101, 103, 105, 108],
        volumes=[1000, 1200, 1500, 1800],
    )
    result = build_intraday_radar_features(
        bars,
        previous_close=98,
        config=RadarConfig(opening_range_minutes=10, min_turnover=1),
    )
    assert result["last_price"] == 108
    assert result["from_open_pct"] == pytest.approx(8.0)
    assert result["from_previous_close_pct"] == pytest.approx((108 / 98 - 1) * 100)
    assert result["vwap"] is not None
    assert result["opening_range_high"] == 104
    assert result["opening_range_breakout"] is True
    assert result["status"] in {"WATCH", "TRIGGER CONFIRMED", "LATE / EXTENDED"}


def test_rvol_requires_multiple_sessions():
    bars = _bars(
        ["2026-11-04 09:15", "2026-11-04 09:20"],
        opens=[100, 101],
        highs=[101, 102],
        lows=[99, 100],
        closes=[100.5, 101.5],
        volumes=[1000, 1000],
    )
    result = build_intraday_radar_features(bars)
    assert result["rvol"] is None
    assert any("insufficient" in reason for reason in result["reasons"])


def test_rvol_uses_prior_session_volume_baseline():
    bars = _bars(
        [
            "2026-11-03 09:15",
            "2026-11-03 09:20",
            "2026-11-04 09:15",
            "2026-11-04 09:20",
        ],
        opens=[100, 100, 100, 101],
        highs=[101, 102, 102, 103],
        lows=[99, 99, 99, 100],
        closes=[100, 101, 101, 102],
        volumes=[1000, 1000, 1500, 1500],
    )
    result = build_intraday_radar_features(bars, config=RadarConfig(min_turnover=1))
    assert result["rvol"] == pytest.approx(1.5)
