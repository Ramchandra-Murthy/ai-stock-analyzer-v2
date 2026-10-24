from __future__ import annotations

from decimal import Decimal

from core.serialization import JsonSerializer
from forecast.domain import FinancialProjection


def run_example() -> None:
    print("--- FORECAST-001: Forecast Domain Example ---")
    projection = FinancialProjection(
        period_label="FY2027-Q1",
        projected_revenue=Decimal("500000000.00"),
        projected_ebitda=Decimal("125000000.00"),
        confidence_score=Decimal("0.90"),
    )

    print(f"Projection Period: {projection.period_label}")
    print(f"Projected EBITDA Margin: {projection.ebitda_margin():.2f}%")
    print("Serialized Projection:\n", JsonSerializer.serialize(projection))


if __name__ == "__main__":
    run_example()
