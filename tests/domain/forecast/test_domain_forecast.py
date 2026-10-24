from __future__ import annotations

from decimal import Decimal

import pytest

from domain.forecast import ForecastAssumption, ForecastMethod, ForecastResult


def test_forecast_assumption_creation() -> None:
    assumption = ForecastAssumption(
        method=ForecastMethod.CAGR, periods=3, growth_rate=Decimal("0.08")
    )
    assert assumption.method == ForecastMethod.CAGR
    assert assumption.periods == 3
    assert assumption.growth_rate == Decimal("0.08")


def test_forecast_result_immutability() -> None:
    result = ForecastResult(
        historical_values=(Decimal("100"), Decimal("110")),
        projected_values=(Decimal("121"), Decimal("133.1")),
        method=ForecastMethod.CAGR,
    )
    assert len(result.projected_values) == 2
    with pytest.raises(Exception):
        result.projected_values.append(Decimal("145"))  # type: ignore
