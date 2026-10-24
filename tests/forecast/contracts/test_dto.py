from __future__ import annotations

from decimal import Decimal

from core.primitives import Currency
from forecast.contracts import ForecastRequestDTO, ForecastResultDTO


def fn():
    return None  # placeholder context if needed


def test_forecast_request_dto_serialization() -> None:
    dto = ForecastRequestDTO(
        ticker="RELIANCE",
        horizon_periods=12,
        confidence_level=Decimal("0.95"),
        base_amount=Decimal("2500.00"),
        currency=Currency.INR,
    )
    data = dto.to_dict()
    assert data["ticker"] == "RELIANCE"
    assert data["horizon_periods"] == 12
    assert data["currency"] == "INR"


def test_forecast_result_dto_serialization() -> None:
    dto = ForecastResultDTO(
        ticker="TCS",
        projected_value=Decimal("4100.50"),
        lower_bound=Decimal("3900.00"),
        upper_bound=Decimal("4300.00"),
        currency=Currency.INR,
    )
    data = dto.to_dict()
    assert data["projected_value"] == "4100.50"
    assert data["currency"] == "INR"
