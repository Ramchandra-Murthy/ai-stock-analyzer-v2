"""Chronological out-of-sample evaluation for the isolated Fibonacci/Gann lab."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from modules.fibonacci_gann.backtest import (
    BacktestConfig,
    BacktestResult,
    Candle,
    run_backtest,
    validate_candles,
)
from modules.fibonacci_gann.validation import SignalFunction


@dataclass(frozen=True)
class WalkForwardFold:
    """One strictly chronological evaluation window."""

    train_start: str
    train_end: str
    test_start: str
    test_end: str
    test_candle_count: int
    result: BacktestResult


def evaluate_walk_forward(
    candles: Sequence[Candle],
    signal_function: SignalFunction,
    config: BacktestConfig,
    *,
    initial_train_size: int,
    test_size: int,
    step_size: int | None = None,
) -> tuple[WalkForwardFold, ...]:
    """Evaluate sequential, non-overlapping test windows after initial history.

    The training window expands with time. The signal callback receives only
    the candle prefix ending at each bar's close. Each fold includes the final
    training candle as an execution boundary so a signal on that candle can enter
    at the first test candle's open. Only test-window candles are scored as the
    fold's evaluation period. Each fold is simulated independently from configured
    capital; results are not a compounded portfolio curve.
    """
    validate_candles(candles)
    if not isinstance(initial_train_size, int) or isinstance(initial_train_size, bool):
        raise ValueError("initial_train_size must be an integer")
    if not isinstance(test_size, int) or isinstance(test_size, bool) or test_size < 2:
        raise ValueError("test_size must be an integer of at least 2")
    if initial_train_size < 1 or initial_train_size >= len(candles):
        raise ValueError("initial_train_size must be at least 1 and smaller than data length")
    if step_size is None:
        step_size = test_size
    if not isinstance(step_size, int) or isinstance(step_size, bool) or step_size < 1:
        raise ValueError("step_size must be a positive integer")
    if step_size < test_size:
        raise ValueError("step_size must be at least test_size to prevent overlapping test windows")

    folds: list[WalkForwardFold] = []
    test_start = initial_train_size
    while test_start < len(candles):
        test_end = min(test_start + test_size, len(candles))
        test_candles = tuple(candles[test_start:test_end])
        if len(test_candles) < 2:
            break

        # Include the final pre-test candle for signal execution alignment. A
        # signal known at its close must be eligible to enter at test_candles[0].open.
        execution_candles = tuple(candles[test_start - 1 : test_end])
        signals: list[bool] = []
        for absolute_index in range(test_start - 1, test_end):
            history = tuple(candles[: absolute_index + 1])
            signal = signal_function(history, config)
            if not isinstance(signal, bool):
                raise ValueError("signal_function must return a bool for each history prefix")
            signals.append(signal)

        result = run_backtest(execution_candles, tuple(signals), config)
        folds.append(
            WalkForwardFold(
                train_start=candles[0].timestamp,
                train_end=candles[test_start - 1].timestamp,
                test_start=test_candles[0].timestamp,
                test_end=test_candles[-1].timestamp,
                test_candle_count=len(test_candles),
                result=result,
            )
        )
        test_start += step_size

    if not folds:
        raise ValueError("not enough candles remain to form a test fold of at least two bars")
    return tuple(folds)
