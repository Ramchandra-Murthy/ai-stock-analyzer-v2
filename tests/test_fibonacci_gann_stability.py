from __future__ import annotations

from dataclasses import replace

import pytest

from modules.fibonacci_gann.backtest import BacktestConfig, Candle, run_backtest
from modules.fibonacci_gann.stability import summarize_walk_forward
from modules.fibonacci_gann.walk_forward import WalkForwardFold


def make_fold(start: int, closes: list[float]) -> WalkForwardFold:
    candles = [
        Candle(f"2026-01-01T09:{15 + i * 5:02d}", close, close + 1, close - 1, close)
        for i, close in enumerate(closes)
    ]
    result = run_backtest(candles, [False] * len(candles), BacktestConfig())
    result = replace(result, total_return_pct=float(start), max_drawdown_pct=float(abs(start) / 2))
    return WalkForwardFold(
        train_start="2025-12-31T09:15",
        train_end="2025-12-31T15:15",
        test_start=candles[0].timestamp,
        test_end=candles[-1].timestamp,
        test_candle_count=len(candles),
        result=result,
    )


def test_summarizes_cross_fold_stability_without_compounding() -> None:
    summary = summarize_walk_forward(
        [make_fold(2, [100, 101]), make_fold(-1, [100, 99]), make_fold(3, [100, 102])],
        minimum_trades=1,
    )
    assert summary.fold_count == 3
    assert summary.total_test_candles == 6
    assert summary.total_trades == 0
    assert summary.profitable_fold_count == 2
    assert summary.profitable_fold_pct == pytest.approx(200 / 3)
    assert summary.mean_fold_return_pct == pytest.approx(4 / 3)
    assert summary.median_fold_return_pct == 2
    assert summary.worst_fold_return_pct == -1
    assert summary.mean_fold_max_drawdown_pct == 1
    assert summary.worst_fold_max_drawdown_pct == 1.5
    assert summary.insufficient_trades is True


def test_rejects_empty_folds() -> None:
    with pytest.raises(ValueError, match="at least one fold"):
        summarize_walk_forward([])


def test_rejects_invalid_trade_threshold() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        summarize_walk_forward([make_fold(0, [100, 101])], minimum_trades=0)


def test_rejects_too_short_fold() -> None:
    fold = make_fold(0, [100, 101])
    with pytest.raises(ValueError, match="at least two"):
        summarize_walk_forward([replace(fold, test_candle_count=1)])
