from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from core.primitives import Currency, Money
from core.primitives.base import ValueObject
from core.validation.rules import StringValidators
from portfolio.domain.position import Position


@dataclass(frozen=True, order=True)
class Portfolio(ValueObject):
    """Immutable aggregate representing an investment portfolio of multiple positions."""

    name: str
    currency: Currency
    positions: tuple[Position, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        StringValidators.non_empty(self.name, "Portfolio Name")
        for pos in self.positions:
            if pos.current_price.currency != self.currency:
                raise ValueError(
                    f"Position currency {pos.current_price.currency} does not match portfolio currency {self.currency}."
                )

    def total_market_value(self) -> Money:
        """Calculates total market value of all positions in the portfolio."""
        total = sum((pos.market_value().amount for pos in self.positions), Decimal("0"))
        return Money(total, self.currency)

    def total_cost(self) -> Money:
        """Calculates total acquisition cost of all positions."""
        total = sum((pos.total_cost().amount for pos in self.positions), Decimal("0"))
        return Money(total, self.currency)

    def total_unrealized_pnl(self) -> Money:
        """Calculates total unrealized profit or loss across the portfolio."""
        total = sum((pos.unrealized_pnl().amount for pos in self.positions), Decimal("0"))
        return Money(total, self.currency)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "currency": str(self.currency),
            "total_market_value": str(self.total_market_value().amount),
            "total_cost": str(self.total_cost().amount),
            "total_unrealized_pnl": str(self.total_unrealized_pnl().amount),
            "positions": [pos.to_dict() for pos in self.positions],
        }
