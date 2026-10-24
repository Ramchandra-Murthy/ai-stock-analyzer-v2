"""Causal moving-average trend filters for Fibonacci-Gann research signals.

A signal is retained only when the signal bar closes above its simple moving
average. The filter is research-only and does not imply predictive value.
"""

from __future__ import annotations

from collections.abc import Sequence

from modules.fibonacci_gann.backtest import Candle, validate_candles


def apply_sma_trend_filter(
    candles: Sequence[Candle],
    signals: Sequence[bool],
    *,
    period: int = 200,
) -> tuple[bool, ...]:
    """Keep entry signals whose close is above the trailing SMA at that close.

    The SMA includes the current signal bar's close, which is known when the
    signal is evaluated. Trades still enter no earlier than the next bar open.
    Signals before a full SMA window are suppressed rather than guessed.
    """
    if isinstance(period, bool) or not isinstance(period, int) or period < 2:
        raise ValueError("period must be an integer of at least 2")
    validate_candles(candles)
    if len(signals) != len(candles):
        raise ValueError("signals length must equal candles length")
    if any(not isinstance(signal, bool) for signal in signals):
        raise ValueError("signals must contain only booleans")

    filtered = [False] * len(candles)
    rolling_sum = 0.0
    closes: list[float] = []
    for index, candle in enumerate(candles):
        closes.append(candle.close)
        rolling_sum += candle.close
        if index >= period:
            rolling_sum -= closes[index - period]
        if index >= period - 1:
            sma = rolling_sum / period
            filtered[index] = signals[index] and candle.close > sma
    return tuple(filtered)
