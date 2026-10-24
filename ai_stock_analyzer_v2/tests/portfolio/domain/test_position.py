from __future__ import annotations

from decimal import Decimal

from core.identifiers import ISIN, CompanySymbol
from core.primitives import Currency, Money, Quantity
from portfolio.domain import Position


def test_position_calculations() -> None:
    pos = Position(
        symbol=CompanySymbol("RELIANCE"),
        isin=ISIN("INE002A01018"),
        quantity=Quantity(Decimal("100")),
        average_cost=Money(Decimal("2500.00"), Currency.INR),
        current_price=Money(Decimal("2800.00"), Currency.INR),
    )

    assert pos.market_value().amount == Decimal("280000.00")
    assert pos.total_cost().amount == Decimal("250000.00")
    assert pos.unrealized_pnl().amount == Decimal("30000.00")
