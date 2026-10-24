"""Confirmed swing-point detection for the isolated Fibonacci/Gann lab."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from modules.fibonacci_gann.market_data import OHLCBar, _price


@dataclass(frozen=True)
class SwingPoint:
    """A pivot confirmed only after the configured right-side bars exist."""

    index: int
    timestamp: datetime
    kind: str
    price: Decimal


def detect_confirmed_swings(
    bars: Sequence[OHLCBar],
    *,
    left_bars: int = 2,
    right_bars: int = 2,
) -> list[SwingPoint]:
    """Return strict pivot highs/lows without using future bars as-of confirmation.

    The final right_bars candles are never emitted as confirmed pivots. Equal
    highs/lows are not pivots, avoiding ambiguous plateau selection. Input bars
    must already have passed OHLC and chronological-order validation.
    """
    if left_bars < 1 or right_bars < 1:
        raise ValueError("left_bars and right_bars must be positive integers")
    if not bars or len(bars) < left_bars + right_bars + 1:
        return []

    results: list[SwingPoint] = []
    for index in range(left_bars, len(bars) - right_bars):
        bar = bars[index]
        neighbours = list(bars[index - left_bars : index]) + list(
            bars[index + 1 : index + right_bars + 1]
        )
        high = _price(bar.high, f"bar {index} high")
        low = _price(bar.low, f"bar {index} low")
        neighbour_highs = [_price(item.high, "neighbour high") for item in neighbours]
        neighbour_lows = [_price(item.low, "neighbour low") for item in neighbours]
        if all(high > value for value in neighbour_highs):
            results.append(SwingPoint(index, bar.timestamp, "high", high))
        if all(low < value for value in neighbour_lows):
            results.append(SwingPoint(index, bar.timestamp, "low", low))

    return sorted(results, key=lambda point: (point.index, point.kind))
