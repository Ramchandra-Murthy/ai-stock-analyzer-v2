from __future__ import annotations

import pytest

from modules.fibonacci_gann.backtest import Candle
from modules.fibonacci_gann.trend_filter import apply_sma_trend_filter


def candles(closes: list[float]) -> list[Candle]:
    return [
        Candle(f"2026-01-{index + 1:02d}", close, close + 1, close - 1, close)
        for index, close in enumerate(closes)
    ]


def test_sma_filter_keeps_only_signals_above_full_trailing_average() -> None:
    data = candles([10, 10, 10, 10, 12, 14])
    signals = [True, True, True, True, True, True]

    assert apply_sma_trend_filter(data, signals, period=3) == (
        False,
        False,
        False,
        False,
        True,
        True,
    )


def test_sma_filter_suppresses_signals_below_or_equal_to_sma() -> None:
    data = candles([10, 12, 14, 12, 12])
    signals = [True] * len(data)

    assert apply_sma_trend_filter(data, signals, period=3) == (
        False,
        False,
        True,
        False,
        False,
    )


def test_sma_filter_preserves_false_signals() -> None:
    data = candles([10, 11, 12, 13])
    assert apply_sma_trend_filter(data, [False] * 4, period=2) == (False,) * 4


@pytest.mark.parametrize("period", [0, 1, -2, True, 2.5])
def test_sma_filter_rejects_invalid_period(period: int) -> None:
    with pytest.raises(ValueError, match="period"):
        apply_sma_trend_filter(candles([10, 11, 12]), [True] * 3, period=period)


def test_sma_filter_rejects_mismatched_signal_length() -> None:
    with pytest.raises(ValueError, match="signals length"):
        apply_sma_trend_filter(candles([10, 11, 12]), [True], period=2)
