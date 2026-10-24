"""Benchmark and sample-size diagnostics for isolated Fibonacci/Gann research."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from modules.fibonacci_gann.backtest import BacktestResult, Candle, validate_candles


@dataclass(frozen=True)
class BenchmarkComparison:
    """Compare a completed strategy result with buy-and-hold over the same candles."""

    strategy_return_pct: float
    benchmark_return_pct: float
    excess_return_pct: float
    strategy_max_drawdown_pct: float
    benchmark_max_drawdown_pct: float
    trade_count: int
    insufficient_trades: bool


def _max_drawdown_pct(values: tuple[float, ...]) -> float:
    peak = values[0]
    maximum = 0.0
    for value in values:
        peak = max(peak, value)
        if peak > 0:
            maximum = max(maximum, (peak - value) / peak)
    return maximum * 100


def compare_with_buy_and_hold(
    candles: tuple[Candle, ...] | list[Candle],
    result: BacktestResult,
    *,
    minimum_trades: int = 10,
) -> BenchmarkComparison:
    """Compare strategy return to close-to-close buy-and-hold on identical bars.

    This is a descriptive benchmark, not a significance test. The caller must
    ensure the result was generated from the same test window and assumptions.
    Buy-and-hold ignores dividends, fees, taxes, and slippage unless represented
    separately by the caller, so comparisons may be optimistic for the benchmark.
    """
    validate_candles(candles)
    if not isinstance(minimum_trades, int) or isinstance(minimum_trades, bool):
        raise ValueError("minimum_trades must be an integer")
    if minimum_trades < 1:
        raise ValueError("minimum_trades must be at least 1")
    if not isfinite(result.total_return_pct) or not isfinite(result.max_drawdown_pct):
        raise ValueError("strategy return and drawdown must be finite")

    first_close = candles[0].close
    benchmark_equity = tuple(candle.close / first_close for candle in candles)
    benchmark_return_pct = (candles[-1].close / first_close - 1) * 100
    return BenchmarkComparison(
        strategy_return_pct=result.total_return_pct,
        benchmark_return_pct=benchmark_return_pct,
        excess_return_pct=result.total_return_pct - benchmark_return_pct,
        strategy_max_drawdown_pct=result.max_drawdown_pct,
        benchmark_max_drawdown_pct=_max_drawdown_pct(benchmark_equity),
        trade_count=len(result.trades),
        insufficient_trades=len(result.trades) < minimum_trades,
    )
