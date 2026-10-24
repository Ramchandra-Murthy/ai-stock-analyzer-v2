"""Tests for strict, confirmed swing-point detection."""

from datetime import UTC, datetime, timedelta

import pytest

from modules.fibonacci_gann.market_data import OHLCBar
from modules.fibonacci_gann.swings import detect_confirmed_swings


def make_bars(highs: list[int], lows: list[int]) -> list[OHLCBar]:
    start = datetime(2026, 10, 16, 10, 0, tzinfo=UTC)
    return [
        OHLCBar(start + timedelta(minutes=i), 10, high, low, 10)
        for i, (high, low) in enumerate(zip(highs, lows, strict=True))
    ]


def test_detects_only_pivots_with_right_side_confirmation() -> None:
    bars = make_bars([10, 12, 15, 12, 11, 13], [8, 7, 6, 7, 8, 7])
    swings = detect_confirmed_swings(bars, left_bars=1, right_bars=2)
    assert [(item.index, item.kind, item.price) for item in swings] == [
        (2, "high", 15),
        (2, "low", 6),
    ]


def test_last_right_side_bars_are_not_emitted_as_confirmed() -> None:
    bars = make_bars([10, 12, 15, 12], [8, 7, 6, 7])
    swings = detect_confirmed_swings(bars, left_bars=1, right_bars=2)
    assert all(item.index < len(bars) - 2 for item in swings)


def test_equal_highs_are_not_strict_pivots() -> None:
    bars = make_bars([10, 15, 15, 11, 10], [8, 7, 7, 8, 9])
    swings = detect_confirmed_swings(bars, left_bars=1, right_bars=1)
    assert not any(item.kind == "high" for item in swings)


@pytest.mark.parametrize("left,right", [(0, 2), (2, 0), (-1, 1)])
def test_window_sizes_must_be_positive(left: int, right: int) -> None:
    with pytest.raises(ValueError):
        detect_confirmed_swings(
            make_bars([10, 12, 15], [8, 7, 6]), left_bars=left, right_bars=right
        )
