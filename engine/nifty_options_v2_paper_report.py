"""Validation and reporting metrics for NIFTY V2 paper sessions."""

from __future__ import annotations

from dataclasses import dataclass

from engine.nifty_options_v2_paper import PaperTrade


@dataclass(frozen=True)
class V2PaperSessionReport:
    """Aggregate metrics for completed simulation-only paper trades."""

    completed_trades: int
    winning_trades: int
    losing_trades: int
    total_points: float
    max_drawdown_points: float


def build_paper_session_report(trades: list[PaperTrade]) -> V2PaperSessionReport:
    """Calculate paper-session performance without capital or cost assumptions."""
    total = 0.0
    peak = 0.0
    max_drawdown = 0.0
    wins = 0
    losses = 0

    for trade in trades:
        points = trade.points_pnl
        if points is None:
            continue
        total += points
        if points > 0:
            wins += 1
        elif points < 0:
            losses += 1
        peak = max(peak, total)
        max_drawdown = max(max_drawdown, peak - total)

    return V2PaperSessionReport(
        completed_trades=wins + losses,
        winning_trades=wins,
        losing_trades=losses,
        total_points=total,
        max_drawdown_points=max_drawdown,
    )
