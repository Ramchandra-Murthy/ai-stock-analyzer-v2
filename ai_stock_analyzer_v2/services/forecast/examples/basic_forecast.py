from __future__ import annotations

import json

from services.forecast.models import ForecastLineItem, ForecastPackage


def run_example() -> None:
    print("Initializing Forecast Domain Layer Example...")

    rev = ForecastLineItem("Revenue", (1000.0, 1150.0, 1322.5))
    ni = ForecastLineItem("Net Income", (150.0, 180.0, 210.0))
    capex = ForecastLineItem("Capex", (50.0, 55.0, 60.0))
    dep = ForecastLineItem("Depreciation", (20.0, 22.0, 24.0))
    wc = ForecastLineItem("Working Capital", (200.0, 220.0, 240.0))
    tax = ForecastLineItem("Tax Rate", (0.25, 0.25, 0.25))

    package = ForecastPackage(
        ticker="TCS",
        years=(2026, 2027, 2028),
        revenue=rev,
        net_income=ni,
        capex=capex,
        depreciation=dep,
        working_capital=wc,
        tax_rate=tax,
        metadata={"author": "AIERP Core Framework", "version": "5.1"},
    )

    serialized = json.dumps(package.to_dict(), indent=4)
    print("\nSerialized Forecast Package Output:")
    print(serialized)


if __name__ == "__main__":
    run_example()
