from __future__ import annotations

from decimal import Decimal

from core.types import Currency, Money, Percentage


def run_example() -> None:
    print("--- CORE-001A: Financial Types Example ---")
    capital = Money(Decimal("1000000.00"), Currency.INR)
    cost_of_capital = Percentage.from_percentage(Decimal("11.5"))
    bps = cost_of_capital.to_basis_points()

    print(f"Principal Capital: {capital.amount} {capital.currency}")
    print(f"Cost of Capital: {float(cost_of_capital)}% ({bps} bps)")


if __name__ == "__main__":
    run_example()
