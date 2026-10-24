from __future__ import annotations

import pytest

from services.forecast.models import ForecastLineItem, ForecastPackage


def test_forecast_line_item_creation_and_serialization() -> None:
    item = ForecastLineItem(name="Revenue", values=(100.0, 110.0, 121.0))
    assert item.name == "Revenue"
    assert item.values == (100.0, 110.0, 121.0)
    data = item.to_dict()
    reconstructed = ForecastLineItem.from_dict(data)
    assert reconstructed == item


def test_forecast_line_item_immutability() -> None:
    item = ForecastLineItem(name="Revenue", values=(100.0, 110.0))
    with pytest.raises(AttributeError):
        item.name = "Modified"  # type: ignore[misc]


def test_forecast_package_serialization() -> None:
    rev = ForecastLineItem("Revenue", (100.0, 120.0))
    ni = ForecastLineItem("Net Income", (10.0, 15.0))
    capex = ForecastLineItem("Capex", (5.0, 6.0))
    dep = ForecastLineItem("Depreciation", (2.0, 2.5))
    wc = ForecastLineItem("Working Capital", (20.0, 22.0))
    tax = ForecastLineItem("Tax Rate", (0.25, 0.25))

    pkg = ForecastPackage(
        ticker="RELIANCE",
        years=(2026, 2027),
        revenue=rev,
        net_income=ni,
        capex=capex,
        depreciation=dep,
        working_capital=wc,
        tax_rate=tax,
        metadata={"model": "test"},
    )
    data = pkg.to_dict()
    reconstructed = ForecastPackage.from_dict(data)
    assert reconstructed.ticker == "RELIANCE"
    assert reconstructed.years == (2026, 2027)
    assert reconstructed.revenue.values == (100.0, 120.0)
    assert reconstructed.metadata["model"] == "test"
