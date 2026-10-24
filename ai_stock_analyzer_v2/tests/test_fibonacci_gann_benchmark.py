from __future__ import annotations

import pytest

from modules.fibonacci_gann.backtest import BacktestConfig, Candle, run_backtest
from modules.fibonacci_gann.benchmark import compare_with_buy_and_hold


def sample_candles() -> list[Candle]:
    return [
        Candle("2026-01-01T09:15", 100, 102, 99, 101),
        Candle("2026-01-01T09:20", 101, 105, 100, 104),
        Candle("2026-01-01T09:25", 104, 106, 102, 103),
        Candle("2026-01-01T09:30", 103, 108, 102, 107),
    ]


def test_compares_strategy_and_buy_and_hold_on_same_window() -> None:
    candles = sample_candles()
    result = run_backtest(
        candles,
        [True, False, False, False],
        BacktestConfig(capital=10_000, max_loss_per_trade=50, stop_distance=5),
    )
    comparison = compare_with_buy_and_hold(candles, result, minimum_trades=2)
    assert comparison.benchmark_return_pct == pytest.approx(100 * (107 / 101 - 1))
    assert comparison.strategy_return_pct == result.total_return_pct
    assert comparison.excess_return_pct == pytest.approx(
        comparison.strategy_return_pct - comparison.benchmark_return_pct
    )
    assert comparison.strategy_max_drawdown_pct == result.max_drawdown_pct
    assert comparison.benchmark_max_drawdown_pct > 0
    assert comparison.trade_count == len(result.trades)
    assert comparison.insufficient_trades is True


def test_sufficient_trade_threshold_is_reported() -> None:
    candles = sample_candles()
    result = run_backtest(candles, [False] * len(candles))
    comparison = compare_with_buy_and_hold(candles, result, minimum_trades=1)
    assert comparison.insufficient_trades is True


@pytest.mark.parametrize("minimum_trades", [0, -1])
def test_rejects_non_positive_minimum_trade_threshold(minimum_trades: int) -> None:
    candles = sample_candles()
    result = run_backtest(candles, [False] * len(candles))
    with pytest.raises(ValueError, match="at least 1"):
        compare_with_buy_and_hold(candles, result, minimum_trades=minimum_trades)


def test_rejects_non_integer_minimum_trade_threshold() -> None:
    candles = sample_candles()
    result = run_backtest(candles, [False] * len(candles))
    with pytest.raises(ValueError, match="must be an integer"):
        compare_with_buy_and_hold(candles, result, minimum_trades=True)
