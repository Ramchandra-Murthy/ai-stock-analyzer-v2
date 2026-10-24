"""Compare a fixed research strategy across caller-labelled market regimes.

This module does not fetch market data or infer regimes. The caller must label
historical windows (for example trending, sideways, volatile) using a documented
rule before evaluation. Each window is backtested independently.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite

from modules.fibonacci_gann.backtest import BacktestConfig, BacktestResult, Candle, run_backtest


@dataclass(frozen=True)
class RegimeResult:
    """Independent backtest results for one caller-labelled regime window."""

    regime: str
    start_index: int
    end_index: int
    candle_count: int
    result: BacktestResult


def evaluate_regime_robustness(
    candles: Sequence[Candle],
    signals: Sequence[bool],
    config: BacktestConfig,
    *,
    regimes: Mapping[str, tuple[int, int]],
) -> tuple[RegimeResult, ...]:
    """Evaluate fixed signals on named, non-overlapping half-open index windows.

    regimes maps a descriptive label to (start, end) indices, with end exclusive.
    Windows must contain at least two candles and may not overlap. Signals are
    evaluated at bar close and the existing backtester enters no earlier than
    the next bar's open. Results are independent, not compounded.
    """
    if len(candles) != len(signals):
        raise ValueError("signals length must equal candles length")
    if not regimes:
        raise ValueError("at least one regime window is required")
    if any(not isinstance(signal, bool) for signal in signals):
        raise ValueError("signals must contain only booleans")

    windows: list[tuple[int, int, str]] = []
    for name, bounds in regimes.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("regime names must be non-empty strings")
        if (
            not isinstance(bounds, tuple)
            or len(bounds) != 2
            or any(not isinstance(value, int) or isinstance(value, bool) for value in bounds)
        ):
            raise ValueError(f"regime {name!r} bounds must be a pair of integer indices")
        start, end = bounds
        if start < 0 or end > len(candles) or end - start < 2:
            raise ValueError(f"regime {name!r} must select at least two in-range candles")
        windows.append((start, end, name))

    ordered = sorted(windows)
    for previous, current in zip(ordered, ordered[1:], strict=False):
        if current[0] < previous[1]:
            raise ValueError("regime windows must not overlap")

    results: list[RegimeResult] = []
    for start, end, name in sorted(windows, key=lambda item: item[0]):
        result = run_backtest(tuple(candles[start:end]), tuple(signals[start:end]), config)
        if not all(
            isfinite(value)
            for value in (
                result.total_return_pct,
                result.max_drawdown_pct,
                result.win_rate_pct,
                result.expectancy_per_trade,
            )
        ):
            raise ValueError(f"regime {name!r} produced non-finite performance metrics")
        results.append(RegimeResult(name, start, end, end - start, result))
    return tuple(results)
