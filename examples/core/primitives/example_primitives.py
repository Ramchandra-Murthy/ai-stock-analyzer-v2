from __future__ import annotations

from decimal import Decimal

from core.primitives import Currency, Money, Percentage, Quantity


def run_example() -> None:
    print("--- CORE-001A: Financial Domain Kernel Primitives Example ---")
    currency = Currency.INR
    price = Money(Decimal("2450.75"), currency)
    shares = Quantity(Decimal("500000000"))
    growth = Percentage.from_percentage(Decimal("14.5"))

    market_cap = Money(price.amount * shares.value, currency)

    print(f"Currency: {currency}")
    print(f"Share Price: {price.amount} {price.currency}")
    print(f"Shares Outstanding: {shares.value:,.0f}")
    print(f"Market Capitalization: {market_cap.amount:,.2f} {market_cap.currency}")
    print(f"Assumed Growth Rate: {float(growth)}% ({growth.to_basis_points()} bps)")
    print(f"Serialized Money: {market_cap.to_dict()}")


if __name__ == "__main__":
    run_example()
