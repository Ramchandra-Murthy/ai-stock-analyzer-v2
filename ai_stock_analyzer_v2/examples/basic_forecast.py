"""
Example: Creating basic forecast domain objects.
"""

from services.forecast.models import (
    ForecastAssumption,
)


def run_example() -> None:
    assumption = ForecastAssumption(
        revenue_growth_rate=0.08,
        ebitda_margin=0.22,
        tax_rate=0.25,
        capex_pct_revenue=0.04,
        working_capital_pct_revenue=0.10,
    )
    print("Forecast Assumption Initialized:", assumption.to_dict())


if __name__ == "__main__":
    run_example()
