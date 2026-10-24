from __future__ import annotations

from decimal import Decimal

from core.types import CompanySymbol, Currency, Money, Percentage, ShareCount


def run_example() -> None:
    symbol: CompanySymbol = "RELIANCE"
    price = Money(Decimal("2450.50"), Currency.INR)
    shares = ShareCount(6_765_432_100)
    growth = Percentage.from_percentage(Decimal("14.5"))

    market_cap = Money(price.amount * Decimal(str(shares.value)), price.currency)
    print(f"Company: {symbol}")
    print(f"Share Price: {price.amount} {price.currency}")
    print(f"Shares: {shares.value:,}")
    print(f"Market Cap: {market_cap.amount:,.2f} {market_cap.currency}")
    print(f"Projected Growth: {float(growth)}%")


if __name__ == "__main__":
    run_example()
