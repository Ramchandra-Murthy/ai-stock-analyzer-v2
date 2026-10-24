from __future__ import annotations

from decimal import Decimal

from core.identifiers import ISIN, CompanySymbol
from core.primitives import Currency, Money, Quantity
from portfolio.domain import Portfolio, Position


def test_portfolio_aggregate() -> None:
    pos1 = Position(
        symbol=CompanySymbol("RELIANCE"),
        isin=ISIN("INE002A01018"),
        quantity=Quantity(Decimal("100")),
        average_cost=Money(Decimal("2500.00"), Currency.INR),
        current_price=Money(Decimal("2800.00"), Currency.INR),
    )
    pos2 = Position(
        symbol=CompanySymbol("TCS"),
        isin=ISIN("INE467B01029"),
        quantity=Quantity(Decimal("50")),
        average_cost=Money(Decimal("3800.00"), Currency.INR),
        current_price=Money(Decimal("4100.00"), Currency.INR),
    )

    portfolio = Portfolio(
        name="Growth Equity Portfolio", currency=Currency.INR, positions=(pos1, pos2)
    )

    assert portfolio.total_market_value().amount == Decimal("485000.00")
    assert portfolio.total_cost().amount == Decimal("440000.00")
    assert portfolio.total_unrealized_pnl().amount == Decimal("45000.00")
