from __future__ import annotations

from decimal import Decimal

from core.primitives import Currency, Money
from core.serialization import JsonSerializer


def run_example() -> None:
    print("--- CORE-004: Serialization Framework Example ---")
    money = Money(Decimal("50000.00"), Currency.INR)
    json_str = JsonSerializer.serialize(money)
    print("Serialized JSON:\n", json_str)


if __name__ == "__main__":
    run_example()
