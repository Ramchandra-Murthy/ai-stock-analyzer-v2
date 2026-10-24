from __future__ import annotations

from decimal import Decimal

from core.types import Money


def run_example() -> None:
    print("--- CORE-001: Money Type Example ---")
    cash_inflow = Money(Decimal("50000.00"), "INR")
    cash_outflow = Money(Decimal("12500.25"), "INR")

    net_cash = cash_inflow - cash_outflow
    print(f"Inflow: {cash_inflow.amount} {cash_inflow.currency}")
    print(f"Outflow: {cash_outflow.amount} {cash_outflow.currency}")
    print(f"Net Balance: {net_cash.amount} {net_cash.currency}")


if __name__ == "__main__":
    run_example()
