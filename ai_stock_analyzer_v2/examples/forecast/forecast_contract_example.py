from __future__ import annotations

from decimal import Decimal

from core.primitives import Currency
from forecast.contracts import ForecastRequestDTO, ForecastResultDTO


def run_example() -> None:
    print("--- FORECAST-002: Contracts & DTOs Example ---")
    request = ForecastRequestDTO(
        ticker="INFY",
        horizon_periods=6,
        confidence_level=Decimal("0.90"),
        base_amount=Decimal("1800.00"),
        currency=Currency.INR,
    )

    result = ForecastResultDTO(
        ticker=request.ticker,
        projected_value=Decimal("1950.25"),
        lower_bound=Decimal("1850.00"),
        upper_bound=Decimal("2050.50"),
        currency=request.currency,
    )

    print("Request DTO:", request.to_dict())
    print("Result DTO:", result.to_dict())


if __name__ == "__main__":
    run_example()
