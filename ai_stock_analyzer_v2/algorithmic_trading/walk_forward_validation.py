"""Sequential out-of-sample evaluation for precomputed point-in-time signals."""

from __future__ import annotations

import pandas as pd

from algorithmic_trading.backtester import run_backtest
from algorithmic_trading.trading_costs import IndiaEquityCostModel


def walk_forward_evaluate(
    prices: pd.Series,
    signals: pd.Series,
    *,
    initial_capital: float = 100_000.0,
    cost_bps: float = 10.0,
    cost_model: IndiaEquityCostModel | None = None,
    min_train_size: int = 252,
    n_splits: int = 5,
) -> pd.DataFrame:
    """Evaluate signals on sequential test windows after a warm-up history.

    Signals must already be generated point-in-time (no future data used to
    create a signal). Each fold is evaluated independently; the initial test
    bar starts flat because the backtester shifts signals by one bar. This
    function does not fit or tune model parameters.
    """
    if min_train_size < 2:
        raise ValueError("min_train_size must be at least 2")
    if n_splits < 1:
        raise ValueError("n_splits must be at least 1")
    if not prices.index.is_unique:
        raise ValueError("prices contains duplicate timestamps")
    if not signals.index.is_unique:
        raise ValueError("signals contains duplicate timestamps")

    if not prices.index.is_monotonic_increasing:
        prices = prices.sort_index()
    if not signals.index.is_monotonic_increasing:
        signals = signals.sort_index()

    aligned = pd.concat(
        [
            pd.to_numeric(prices, errors="coerce").rename("price"),
            pd.to_numeric(signals, errors="coerce").rename("signal"),
        ],
        axis=1,
    ).dropna()
    aligned = aligned[aligned["price"] > 0]

    if len(aligned) <= min_train_size:
        raise ValueError("not enough observations after min_train_size")

    available = len(aligned) - min_train_size
    if available < n_splits * 2:
        raise ValueError("each test fold must contain at least two observations")

    fold_size = available // n_splits
    rows: list[dict[str, float | int | str]] = []
    for fold in range(n_splits):
        start = min_train_size + fold * fold_size
        stop = len(aligned) if fold == n_splits - 1 else start + fold_size
        test = aligned.iloc[start:stop]
        _, metrics = run_backtest(
            prices=test["price"],
            signals=test["signal"],
            initial_capital=initial_capital,
            cost_bps=cost_bps,
            cost_model=cost_model,
        )
        rows.append(
            {
                "fold": fold + 1,
                "test_start": str(test.index[0]),
                "test_end": str(test.index[-1]),
                "observations": len(test),
                "total_return": metrics.total_return,
                "cagr": metrics.cagr if metrics.cagr is not None else float("nan"),
                "max_drawdown": metrics.max_drawdown,
                "buy_hold_return": metrics.buy_hold_return,
                "trade_count": metrics.trade_count,
                "win_rate": metrics.win_rate,
                "profit_factor": (
                    metrics.profit_factor if metrics.profit_factor is not None else float("nan")
                ),
                "annualized_volatility": metrics.volatility,
                "sharpe_ratio": (
                    metrics.sharpe_ratio if metrics.sharpe_ratio is not None else float("nan")
                ),
                "sortino_ratio": (
                    metrics.sortino_ratio if metrics.sortino_ratio is not None else float("nan")
                ),
                "calmar_ratio": (
                    metrics.calmar_ratio if metrics.calmar_ratio is not None else float("nan")
                ),
            }
        )
    return pd.DataFrame(rows)
