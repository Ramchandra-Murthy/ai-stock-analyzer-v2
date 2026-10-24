from __future__ import annotations

from datetime import date
from decimal import Decimal

from core import (
    ISIN,
    CompanySymbol,
    Currency,
    DateRange,
    ExchangeCode,
    FiscalPeriod,
    Industry,
    Money,
    Percentage,
    Quantity,
    Sector,
)


def run_demo() -> None:
    print("==================================================")
    print("   AI Institutional Equity Research Platform")
    print("   Core Financial Domain Kernel - Demo (CORE-001)")
    print("==================================================")

    # Identifiers & Classifications
    symbol = CompanySymbol("reliance")
    isin = ISIN("INE002A01018")
    exchange = ExchangeCode.NSE
    sector = Sector("Energy")
    industry = Industry("Oil & Gas Refining")

    # Financial Primitives
    currency = Currency.INR
    share_price = Money(Decimal("2850.50"), currency)
    shares_count = Quantity(Decimal("6765432100"))
    market_cap = Money(share_price.amount * shares_count.value, currency)
    expected_growth = Percentage.from_percentage(Decimal("12.5"))

    # Fiscal Period
    fiscal_period = FiscalPeriod.from_ints(2026, "Q1")
    period_range = DateRange(date(2026, 4, 1), date(2026, 6, 30))

    print(f"\n[Entity] {symbol} ({isin}) listed on {exchange}")
    print(f"[Classification] {sector} -> {industry}")
    print(
        f"[Market Data] Price: {share_price.amount} {share_price.currency} | Shares: {shares_count.value:,.0f}"
    )
    print(f"[Valuation] Market Capitalization: {market_cap.amount:,.2f} {market_cap.currency}")
    print(
        f"[Assumptions] Projected Growth: {float(expected_growth)}% ({expected_growth.to_basis_points()} bps)"
    )
    print(
        f"[Temporal] Active Period: {fiscal_period} ({period_range.start_date} to {period_range.end_date}, {period_range.duration_days()} days)"
    )
    print("\nCore Kernel verification successfully completed.")


if __name__ == "__main__":
    run_demo()
