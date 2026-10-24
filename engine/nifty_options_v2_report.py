"""Reporting metrics for NIFTY Options Book V2 backtests."""

from __future__ import annotations

from dataclasses import dataclass

from engine.nifty_options_v2_monthly import MonthlyV2Trade


@dataclass(frozen=True)
class V2BacktestReport:
    """Aggregate performance metrics for a completed monthly backtest."""

    total_points: float
    winning_months: int
    losing_months: int
    win_rate: float
    max_drawdown_points: float


def build_report(results: list[MonthlyV2Trade]) -> V2BacktestReport:
    """Calculate aggregate metrics without assuming capital or costs."""
    total = 0.0
    peak = 0.0
    max_drawdown = 0.0
    wins = 0
    losses = 0
    for result in results:
        points = result.points_pnl
        total += points
        if points > 0:
            wins += 1
        elif points < 0:
            losses += 1
        peak = max(peak, total)
        max_drawdown = max(max_drawdown, peak - total)
    traded = wins + losses
    win_rate = wins / traded if traded else 0.0
    return V2BacktestReport(total, wins, losses, win_rate, max_drawdown)
