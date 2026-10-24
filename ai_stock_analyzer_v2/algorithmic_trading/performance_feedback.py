"""Performance and feedback analytics for the algorithmic trading pipeline.

The module keeps the Chapter 10 feedback loop auditable: completed trade
outcomes can be grouped by signal direction, regime, symbol, and allocation
metadata without changing the existing paper-trading or journal interfaces.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class PerformanceSummary:
    """Aggregate performance metrics for a completed-trade set."""

    trades: int
    wins: int
    losses: int
    win_rate: float
    total_pnl: float
    average_pnl: float
    profit_factor: float


def _require_columns(trades: pd.DataFrame) -> None:
    required = {"pnl"}
    missing = required.difference(trades.columns)
    if missing:
        raise ValueError(f"trades is missing required columns: {sorted(missing)}")


def summarize_performance(trades: pd.DataFrame) -> PerformanceSummary:
    """Summarize completed trade P&L without assuming a strategy winner."""
    _require_columns(trades)
    pnl = pd.to_numeric(trades["pnl"], errors="coerce").dropna()
    wins = int((pnl > 0).sum())
    losses = int((pnl < 0).sum())
    gross_profit = float(pnl[pnl > 0].sum())
    gross_loss = float(-pnl[pnl < 0].sum())
    profit_factor = (
        gross_profit / gross_loss if gross_loss > 0 else float("inf") if gross_profit > 0 else 0.0
    )
    return PerformanceSummary(
        trades=int(len(pnl)),
        wins=wins,
        losses=losses,
        win_rate=float(wins / len(pnl)) if len(pnl) else 0.0,
        total_pnl=float(pnl.sum()),
        average_pnl=float(pnl.mean()) if len(pnl) else 0.0,
        profit_factor=profit_factor,
    )


def group_performance(trades: pd.DataFrame, by: str) -> pd.DataFrame:
    """Return auditable P&L metrics grouped by one trade attribute."""
    _require_columns(trades)
    if by not in trades.columns:
        raise ValueError(f"trades is missing grouping column: {by}")

    frame = trades[[by, "pnl"]].copy()
    frame["pnl"] = pd.to_numeric(frame["pnl"], errors="coerce")
    frame = frame.dropna(subset=["pnl"])
    if frame.empty:
        return pd.DataFrame(
            columns=[by, "trades", "wins", "losses", "win_rate", "total_pnl", "average_pnl"]
        )

    grouped = frame.groupby(by, dropna=False)["pnl"]
    result = grouped.agg(
        trades="count",
        wins=lambda values: int((values > 0).sum()),
        losses=lambda values: int((values < 0).sum()),
        total_pnl="sum",
        average_pnl="mean",
    ).reset_index()
    result["win_rate"] = result["wins"] / result["trades"]
    return result[[by, "trades", "wins", "losses", "win_rate", "total_pnl", "average_pnl"]]


def equity_curve(trades: pd.DataFrame, initial_capital: float = 100_000.0) -> pd.Series:
    """Build an event-time equity curve from completed trade P&L."""
    _require_columns(trades)
    if initial_capital <= 0:
        raise ValueError("initial_capital must be greater than zero")
    pnl = pd.to_numeric(trades["pnl"], errors="coerce").fillna(0.0)
    return (initial_capital + pnl.cumsum()).rename("equity")


def drawdown_curve(equity: pd.Series) -> pd.Series:
    """Calculate percentage drawdown from the running equity peak."""
    values = pd.to_numeric(equity, errors="coerce").dropna()
    if values.empty:
        return pd.Series(dtype=float, name="drawdown")
    peak = values.cummax()
    return (values / peak - 1.0).rename("drawdown")


def feedback_report(trades: pd.DataFrame) -> dict[str, pd.DataFrame | PerformanceSummary]:
    """Produce the core feedback views used by the next dashboard layer."""
    summary = summarize_performance(trades)
    report: dict[str, pd.DataFrame | PerformanceSummary] = {"summary": summary}
    for field in ("symbol", "signal", "regime"):
        if field in trades.columns:
            report[field] = group_performance(trades, field)
    return report
