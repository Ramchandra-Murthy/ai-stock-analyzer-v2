from __future__ import annotations

from core.primitives.currency import Currency
from core.primitives.money import Money
from core.primitives.percentage import Percentage
from core.primitives.quantity import Quantity


def run_demo() -> None:
    print("--- CORE-001A: Financial Primitive Value Objects Demo ---")
    cash = Money("1000000", Currency.INR)
    growth = Percentage(12.5)
    shares = Quantity(150000000)
    enterprise_value = cash * 5

    print(f"Cash Balance: {cash.amount} {cash.currency}")
    print(f"Growth Percentage: {growth.value}% (Fraction: {growth.to_fraction()})")
    print(f"Share Quantity: {shares.value:,}")
    print(f"Implied Enterprise Value: {enterprise_value.amount} {enterprise_value.currency}")
    print(f"Serialized Money: {cash.to_dict()}")


if __name__ == "__main__":
    run_demo()
