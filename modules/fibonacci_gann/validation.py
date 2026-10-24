"""Leakage-resistant parameter validation for the isolated Fibonacci/Gann lab.

A signal callback receives only the candle history available at that bar's close.
The existing backtester then enters no earlier than the following bar's open.
This is a deterministic research aid, not evidence of a profitable strategy.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from modules.fibonacci_gann.backtest import (
    BacktestConfig,
    BacktestResult,
    Candle,
    run_backtest,
    validate_candles,
)

SignalFunction = Callable[[Sequence[Candle], BacktestConfig], bool]


@dataclass(frozen=True)
class ValidationCase:
    """Named set of backtest assumptions for a sensitivity comparison."""

    name: str
    config: BacktestConfig


@dataclass(frozen=True)
class ValidationOutcome:
    """Backtest output linked to the assumptions that produced it."""

    name: str
    config: BacktestConfig
    result: BacktestResult


def build_causal_signals(
    candles: Sequence[Candle],
    signal_function: SignalFunction,
    config: BacktestConfig,
) -> tuple[bool, ...]:
    """Build one signal per bar without exposing any future candles.

    The callback is invoked with a growing prefix ending at the current bar.
    It must return a plain bool and must not fetch external/live data. A signal
    at bar i can only be executed by run_backtest at bar i+1's open.
    """
    validate_candles(candles)
    signals: list[bool] = []
    for end in range(1, len(candles) + 1):
        signal = signal_function(tuple(candles[:end]), config)
        if not isinstance(signal, bool):
            raise ValueError("signal_function must return a bool for each history prefix")
        signals.append(signal)
    return tuple(signals)


def evaluate_parameter_sensitivity(
    candles: Sequence[Candle],
    cases: Sequence[ValidationCase],
    signal_function: SignalFunction,
) -> tuple[ValidationOutcome, ...]:
    """Run deterministic sensitivity cases on the same fixed candle sequence.

    Each case builds signals causally from the same data and runs the existing
    conservative backtester. The loss ceiling may not exceed starting capital.
    Duplicate/blank case names are rejected to keep comparisons unambiguous.
    """
    validate_candles(candles)
    if not cases:
        raise ValueError("at least one validation case is required")
    names = [case.name.strip() for case in cases]
    if any(not name for name in names):
        raise ValueError("case names must be non-empty")
    if len(set(names)) != len(names):
        raise ValueError("case names must be unique")
    outcomes: list[ValidationOutcome] = []
    for case in cases:
        if case.config.max_loss_per_trade > case.config.capital:
            raise ValueError("max_loss_per_trade cannot exceed starting capital")
        signals = build_causal_signals(candles, signal_function, case.config)
        result = run_backtest(candles, signals, case.config)
        outcomes.append(ValidationOutcome(case.name, case.config, result))
    return tuple(outcomes)
