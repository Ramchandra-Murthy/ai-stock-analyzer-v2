"""Parameter-sensitivity diagnostics for point-in-time sentiment backtests."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from itertools import product

import pandas as pd

from ai_trading.news_schema import NewsRecord
from ai_trading.sentiment_walk_forward_backtest import evaluate_sentiment_walk_forward


def evaluate_sentiment_robustness_grid(
    records: Sequence[NewsRecord],
    bars_by_symbol: Mapping[str, pd.DataFrame],
    *,
    horizons: Iterable[int] = (3, 5, 10),
    sentiment_thresholds: Iterable[float] = (0.1, 0.2, 0.3),
    transaction_costs_bps: Iterable[float] = (5.0, 10.0, 20.0),
    folds: int = 4,
) -> pd.DataFrame:
    """Evaluate a fixed parameter grid and summarize fold-level stability.

    This is a sensitivity diagnostic, not parameter optimization. Every grid
    point is evaluated independently using the same chronological event folds.
    """
    horizon_values = tuple(horizons)
    threshold_values = tuple(sentiment_thresholds)
    cost_values = tuple(transaction_costs_bps)
    if not horizon_values or not threshold_values or not cost_values:
        raise ValueError("parameter grids must be non-empty")

    rows: list[dict[str, int | float]] = []
    for horizon, threshold, cost in product(
        horizon_values, threshold_values, cost_values
    ):
        result = evaluate_sentiment_walk_forward(
            records,
            bars_by_symbol,
            horizon=horizon,
            folds=folds,
            sentiment_threshold=threshold,
            transaction_cost_bps=cost,
        )
        fold_returns = result.folds.get(
            "total_return", pd.Series(dtype=float)
        ).astype(float)
        fold_drawdowns = result.folds.get(
            "max_drawdown", pd.Series(dtype=float)
        ).astype(float)
        fold_win_rates = result.folds.get(
            "win_rate", pd.Series(dtype=float)
        ).astype(float)
        rows.append(
            {
                "horizon": int(horizon),
                "sentiment_threshold": float(threshold),
                "transaction_cost_bps": float(cost),
                "events": int(len(result.events)),
                "folds": int(len(result.folds)),
                "mean_fold_return": float(fold_returns.mean())
                if len(fold_returns)
                else 0.0,
                "worst_fold_return": float(fold_returns.min())
                if len(fold_returns)
                else 0.0,
                "fold_return_std": float(fold_returns.std(ddof=0))
                if len(fold_returns)
                else 0.0,
                "positive_fold_rate": float((fold_returns > 0.0).mean())
                if len(fold_returns)
                else 0.0,
                "mean_fold_win_rate": float(fold_win_rates.mean())
                if len(fold_win_rates)
                else 0.0,
                "worst_fold_drawdown": float(fold_drawdowns.min())
                if len(fold_drawdowns)
                else 0.0,
            }
        )
    return pd.DataFrame(rows)
