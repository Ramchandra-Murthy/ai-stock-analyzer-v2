"""Cost, capital, and risk helpers for NIFTY Options Book V2."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class V2CostModel:
    """Explicit per-trade cost assumptions."""

    entry_cost: float = 0.0
    exit_cost: float = 0.0
    slippage_points: float = 0.0

    def __post_init__(self) -> None:
        if min(self.entry_cost, self.exit_cost, self.slippage_points) < 0:
            raise ValueError("costs and slippage must be non-negative")


def net_points(
    gross_points: float,
    *,
    lot_size: int,
    costs: V2CostModel,
) -> float:
    """Convert gross points into net points after explicit costs and slippage."""
    if lot_size <= 0:
        raise ValueError("lot_size must be positive")
    total_cost_points = (costs.entry_cost + costs.exit_cost) / lot_size
    return gross_points - total_cost_points - costs.slippage_points


def net_pnl(
    gross_points: float,
    *,
    lot_size: int,
    costs: V2CostModel,
) -> float:
    """Return net rupee P&L after explicit costs and slippage."""
    return net_points(gross_points, lot_size=lot_size, costs=costs) * lot_size


def max_drawdown(values: Sequence[float]) -> float:
    """Return maximum peak-to-trough drawdown as a positive amount."""
    peak = 0.0
    drawdown = 0.0
    for value in values:
        peak = max(peak, value)
        drawdown = max(drawdown, peak - value)
    return drawdown


def capital_return(net_profit: float, capital: float) -> float:
    """Return simple net return as a decimal fraction."""
    if capital <= 0:
        raise ValueError("capital must be positive")
    return net_profit / capital
