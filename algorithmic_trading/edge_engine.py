"""Trading-edge and expectancy calculations.

Chapter 5 frames trading edge as a measurable number. This module keeps
that concept explicit for NSE/BSE strategy research.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class EdgeMetrics:
    """Summary statistics for a collection of realized trade returns."""

    trades: int
    win_rate: float
    average_win: float
    average_loss: float
    expectancy: float
    profit_factor: float | None


def calculate_edge(returns: pd.Series) -> EdgeMetrics:
    """Calculate win rate, average win/loss and arithmetic expectancy."""
    values = pd.to_numeric(returns, errors="coerce").dropna()
    if values.empty:
        return EdgeMetrics(0, 0.0, 0.0, 0.0, 0.0, None)

    wins = values[values > 0]
    losses = values[values < 0]
    trades = len(values)
    win_rate = len(wins) / trades
    average_win = float(wins.mean()) if not wins.empty else 0.0
    average_loss = float(abs(losses.mean())) if not losses.empty else 0.0
    expectancy = win_rate * average_win - (1.0 - win_rate) * average_loss
    gross_profit = float(wins.sum())
    gross_loss = float(abs(losses.sum()))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else None

    return EdgeMetrics(
        trades=trades,
        win_rate=win_rate,
        average_win=average_win,
        average_loss=average_loss,
        expectancy=float(expectancy),
        profit_factor=profit_factor,
    )


def rolling_expectancy(returns: pd.Series, window: int = 30) -> pd.Series:
    """Calculate rolling arithmetic expectancy across realized trades."""
    if window <= 0:
        raise ValueError("window must be greater than zero")

    values = pd.to_numeric(returns, errors="coerce")

    def _expectancy(sample: pd.Series) -> float:
        return calculate_edge(sample).expectancy

    return values.rolling(window=window, min_periods=window).apply(
        _expectancy,
        raw=False,
    )
