"""Unit tests for the research-only Gann/Fibonacci calculation core."""

import pandas as pd
import pytest

from modules.gann_fibonacci_time.anchors import detect_confirmed_pivots
from modules.gann_fibonacci_time.confluence import eligible_time_zone_indices, find_confluence
from modules.gann_fibonacci_time.fibonacci_time_zones import project_time_zones
from modules.gann_fibonacci_time.gann_fan import project_gann_fan
from modules.gann_fibonacci_time.validation import validate_ohlcv


def candles(highs, lows=None):
    lows = lows if lows is not None else [value - 2 for value in highs]
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=len(highs), freq="D"),
            "open": [(high + low) / 2 for high, low in zip(highs, lows, strict=True)],
            "high": highs,
            "low": lows,
            "close": [(high + low) / 2 for high, low in zip(highs, lows, strict=True)],
        }
    )


def test_validate_ohlcv_returns_copy_and_rejects_duplicate_timestamps():
    frame = candles([10, 11, 12])
    result = validate_ohlcv(frame)
    assert result is not frame
    assert len(result) == 3
    duplicate = frame.copy()
    duplicate.loc[2, "timestamp"] = duplicate.loc[1, "timestamp"]
    with pytest.raises(ValueError, match="Duplicate"):
        validate_ohlcv(duplicate)


def test_validate_ohlcv_rejects_unsorted_and_invalid_ohlc():
    frame = candles([10, 11, 12])
    frame.loc[[0, 1], "timestamp"] = frame.loc[[1, 0], "timestamp"].to_numpy()
    with pytest.raises(ValueError, match="chronological"):
        validate_ohlcv(frame)
    invalid = candles([10, 11, 12])
    invalid.loc[1, "high"] = 1
    with pytest.raises(ValueError, match="OHLC"):
        validate_ohlcv(invalid)


def test_project_time_zones_uses_trading_bar_indices_and_bounds():
    assert project_time_zones(2, 40, (3, 5, 8, 11, 21, 34)) == [
        {"interval": 3, "bar_index": 5},
        {"interval": 5, "bar_index": 7},
        {"interval": 8, "bar_index": 10},
        {"interval": 11, "bar_index": 13},
        {"interval": 21, "bar_index": 23},
        {"interval": 34, "bar_index": 36},
    ]
    assert project_time_zones(35, 40, (3, 5)) == [{"interval": 3, "bar_index": 38}]


@pytest.mark.parametrize(
    ("anchor_index", "total_bars"),
    [(-1, 10), (10, 10), (0, 0)],
)
def test_project_time_zones_rejects_invalid_bounds(anchor_index, total_bars):
    with pytest.raises(ValueError):
        project_time_zones(anchor_index, total_bars)


def test_pivots_include_confirmation_index_not_only_pivot_index():
    frame = candles([10, 11, 15, 12, 11, 10, 12], [8, 9, 10, 8, 7, 5, 8])
    pivots = detect_confirmed_pivots(frame, left_bars=1, right_bars=1)
    peak = next(item for item in pivots if item["kind"] == "high")
    assert peak["pivot_index"] == 2
    assert peak["confirmed_at_index"] == 3
    assert peak["price"] == 15.0


def test_pivot_detector_rejects_invalid_confirmation_window():
    with pytest.raises(ValueError, match="right_bars"):
        detect_confirmed_pivots(candles([10, 11, 12]), right_bars=0)


def test_gann_fan_is_deterministic_and_uses_explicit_scale():
    levels = project_gann_fan(5, 100, [5, 7], price_per_bar=2, ratios=(1, 2))
    assert levels == [
        {"target_index": 5, "ratio": 1.0, "price": 100.0, "direction": "up"},
        {"target_index": 5, "ratio": 2.0, "price": 100.0, "direction": "up"},
        {"target_index": 7, "ratio": 1.0, "price": 104.0, "direction": "up"},
        {"target_index": 7, "ratio": 2.0, "price": 108.0, "direction": "up"},
    ]
    down = project_gann_fan(5, 100, [7], price_per_bar=2, direction=-1, ratios=(1,))
    assert down[0]["price"] == 96.0


def test_gann_fan_rejects_invalid_scale_and_pre_anchor_target():
    with pytest.raises(ValueError, match="price_per_bar"):
        project_gann_fan(0, 100, [1], price_per_bar=0)
    with pytest.raises(ValueError, match="Target indices"):
        project_gann_fan(3, 100, [2], price_per_bar=1)


def test_confluence_only_matches_time_bars_within_price_tolerance():
    projections = [
        {"target_index": 8, "ratio": 1.0, "price": 100.0},
        {"target_index": 9, "ratio": 1.0, "price": 100.0},
    ]
    result = find_confluence([8], projections, {8: 100.4, 9: 100.0}, tolerance_pct=0.5)
    assert len(result) == 1
    assert result[0]["bar_index"] == 8
    assert result[0]["distance_pct"] == pytest.approx(0.4)


def test_confluence_rejects_invalid_tolerance():
    with pytest.raises(ValueError, match="tolerance_pct"):
        find_confluence([], [], {}, tolerance_pct=100)


def test_historical_confluence_zones_exclude_bars_before_anchor_confirmation():
    zones = [103, 105, 108, 120]
    assert eligible_time_zone_indices(zones, confirmed_at_index=105, total_bars=110) == [
        105,
        108,
    ]


def test_historical_confluence_zone_filter_handles_manual_anchor_and_invalid_inputs():
    assert eligible_time_zone_indices([3, 5, 8], confirmed_at_index=5, total_bars=9) == [
        5,
        8,
    ]
    with pytest.raises(ValueError, match="confirmed_at_index"):
        eligible_time_zone_indices([1, 2], confirmed_at_index=-1, total_bars=3)
    with pytest.raises(ValueError, match="total_bars"):
        eligible_time_zone_indices([1, 2], confirmed_at_index=1, total_bars=-1)
