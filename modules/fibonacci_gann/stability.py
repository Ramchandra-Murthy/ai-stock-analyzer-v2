"""Stability summaries for independently evaluated walk-forward folds."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from statistics import mean, median

from modules.fibonacci_gann.walk_forward import WalkForwardFold


@dataclass(frozen=True)
class WalkForwardStability:
    """Descriptive cross-fold consistency metrics; folds are not compounded."""

    fold_count: int
    total_test_candles: int
    total_trades: int
    profitable_fold_count: int
    profitable_fold_pct: float
    mean_fold_return_pct: float
    median_fold_return_pct: float
    worst_fold_return_pct: float
    mean_fold_max_drawdown_pct: float
    worst_fold_max_drawdown_pct: float
    insufficient_trades: bool


def summarize_walk_forward(
    folds: tuple[WalkForwardFold, ...] | list[WalkForwardFold],
    *,
    minimum_trades: int = 10,
) -> WalkForwardStability:
    """Summarize fold consistency without pretending separate folds are compounded.

    The caller is responsible for passing folds from one walk-forward evaluation
    and for avoiding overlap if interpreting the output as a chronological test.
    """
    if not folds:
        raise ValueError("at least one fold is required")
    if not isinstance(minimum_trades, int) or isinstance(minimum_trades, bool):
        raise ValueError("minimum_trades must be an integer")
    if minimum_trades < 1:
        raise ValueError("minimum_trades must be at least 1")

    returns = [fold.result.total_return_pct for fold in folds]
    drawdowns = [fold.result.max_drawdown_pct for fold in folds]
    if not all(isfinite(value) for value in returns + drawdowns):
        raise ValueError("fold returns and drawdowns must be finite")
    if any(fold.test_candle_count < 2 for fold in folds):
        raise ValueError("each fold must contain at least two test candles")

    profitable = sum(value > 0 for value in returns)
    trade_count = sum(len(fold.result.trades) for fold in folds)
    return WalkForwardStability(
        fold_count=len(folds),
        total_test_candles=sum(fold.test_candle_count for fold in folds),
        total_trades=trade_count,
        profitable_fold_count=profitable,
        profitable_fold_pct=profitable / len(folds) * 100,
        mean_fold_return_pct=mean(returns),
        median_fold_return_pct=median(returns),
        worst_fold_return_pct=min(returns),
        mean_fold_max_drawdown_pct=mean(drawdowns),
        worst_fold_max_drawdown_pct=max(drawdowns),
        insufficient_trades=trade_count < minimum_trades,
    )
