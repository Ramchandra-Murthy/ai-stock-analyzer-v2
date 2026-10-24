from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.identifiers import ISIN, CompanySymbol
from core.primitives import Money, Quantity
from core.primitives.base import ValueObject
from core.validation.rules import NumericValidators


@dataclass(frozen=True, order=True)
class Position(ValueObject):
    """Immutable representation of an equity investment position."""

    symbol: CompanySymbol
    isin: ISIN
    quantity: Quantity
    average_cost: Money
    current_price: Money

    def __post_init__(self) -> None:
        if self.average_cost.currency != self.current_price.currency:
            raise ValueError("Average cost currency must match current price currency.")
        NumericValidators.non_negative(self.quantity.value, "Position Quantity")

    def market_value(self) -> Money:
        """Calculates total market value of the position."""
        total_val = self.quantity.value * self.current_price.amount
        return Money(total_val, self.current_price.currency)

    def total_cost(self) -> Money:
        """Calculates total acquisition cost of the position."""
        cost_val = self.quantity.value * self.average_cost.amount
        return Money(cost_val, self.average_cost.currency)

    def unrealized_pnl(self) -> Money:
        """Calculates unrealized profit or loss."""
        val = self.market_value().amount - self.total_cost().amount
        return Money(val, self.current_price.currency)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": str(self.symbol),
            "isin": str(self.isin),
            "quantity": str(self.quantity.value),
            "average_cost": str(self.average_cost.amount),
            "current_price": str(self.current_price.amount),
            "currency": str(self.current_price.currency),
            "market_value": str(self.market_value().amount),
            "unrealized_pnl": str(self.unrealized_pnl().amount),
        }
