from __future__ import annotations

from decimal import Decimal

from core.identifiers import ISIN, CompanySymbol
from core.primitives import Currency, Money, Quantity
from core.serialization import JsonSerializer
from portfolio.domain import Position


def run_example() -> None:
    print("--- PORTFOLIO-001: Portfolio Domain Example ---")
    pos = Position(
        symbol=CompanySymbol("TCS"),
        isin=ISIN("INE467B01029"),
        quantity=Quantity(Decimal("50")),
        average_cost=Money(Decimal("3800.00"), Currency.INR),
        current_price=Money(Decimal("4100.00"), Currency.INR),
    )

    print(
        f"Position: {pos.symbol} | PnL: {pos.unrealized_pnl().amount} {pos.unrealized_pnl().currency}"
    )
    print("Serialized Position:\n", JsonSerializer.serialize(pos))


if __name__ == "__main__":
    run_example()
