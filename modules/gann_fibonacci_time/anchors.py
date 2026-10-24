"""Causal swing-point detection for Gann/Fibonacci research."""

from __future__ import annotations

import pandas as pd

from modules.gann_fibonacci_time.validation import validate_ohlcv


def detect_confirmed_pivots(
    candles: pd.DataFrame,
    left_bars: int = 3,
    right_bars: int = 3,
) -> list[dict[str, int | str | float]]:
    """Detect strict local highs/lows and include their confirmation bar index."""
    if isinstance(left_bars, bool) or not isinstance(left_bars, int) or left_bars < 1:
        raise ValueError("left_bars must be a positive integer.")
    if isinstance(right_bars, bool) or not isinstance(right_bars, int) or right_bars < 1:
        raise ValueError("right_bars must be a positive integer.")
    frame = validate_ohlcv(candles)
    highs, lows = frame["high"].tolist(), frame["low"].tolist()
    pivots: list[dict[str, int | str | float]] = []
    for index in range(left_bars, len(frame) - right_bars):
        high_window = highs[index - left_bars : index + right_bars + 1]
        low_window = lows[index - left_bars : index + right_bars + 1]
        if highs[index] == max(high_window) and high_window.count(highs[index]) == 1:
            pivots.append(
                {
                    "kind": "high",
                    "pivot_index": index,
                    "confirmed_at_index": index + right_bars,
                    "price": float(highs[index]),
                }
            )
        if lows[index] == min(low_window) and low_window.count(lows[index]) == 1:
            pivots.append(
                {
                    "kind": "low",
                    "pivot_index": index,
                    "confirmed_at_index": index + right_bars,
                    "price": float(lows[index]),
                }
            )
    return sorted(
        pivots,
        key=lambda item: (int(item["confirmed_at_index"]), int(item["pivot_index"])),
    )
