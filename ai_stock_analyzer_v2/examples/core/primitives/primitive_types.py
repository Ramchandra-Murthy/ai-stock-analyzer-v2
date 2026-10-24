from __future__ import annotations

from decimal import Decimal

from core.primitives import Currency, Money, Percentage, Quantity


def run_example() -> None:
    print("--- CORE-001A: Financial Primitives Example ---")
    price = Money(Decimal("2850.75"), Currency.INR)
    qty = Quantity(Decimal("150"))
    total = Money(price.amount * qty.value, price.currency)
    growth = Percentage.from_percentage(Decimal("14.2"))

    print(f"Price per share: {price.amount} {price.currency}")
    print(f"Quantity: {qty.value}")
    print(f"Total Valuation: {total.amount} {total.currency}")
    print(f"Projected Growth: {float(growth)}% ({growth.to_basis_points()} bps)")


if __name__ == "__main__":
    run_example()
