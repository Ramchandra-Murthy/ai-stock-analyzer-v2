"""
==================================================
Example...
==================================================
"""

from __future__ import annotations

from services.forecast.models import (
    CapexForecast,
    ConfidenceLevel,
    DepreciationForecast,
    ForecastAssumption,
    ForecastConfidence,
    ForecastMethod,
    ForecastScenario,
    MarginForecast,
    RevenueForecast,
    TaxForecast,
    TerminalGrowthForecast,
    WorkingCapitalForecast,
)


def main() -> None:
    print("Initializing canonical forecast scenario...")

    scenario = ForecastScenario(
        scenario_name="Enterprise Base Case",
        method=ForecastMethod.CAGR,
        revenue=RevenueForecast(values=(5000.0, 5500.0, 6050.0), years=(2026, 2027, 2028)),
        margins=MarginForecast(values=(0.22, 0.23, 0.24), years=(2026, 2027, 2028)),
        capex=CapexForecast(values=(250.0, 275.0, 300.0), years=(2026, 2027, 2028)),
        depreciation=DepreciationForecast(values=(100.0, 110.0, 120.0), years=(2026, 2027, 2028)),
        working_capital=WorkingCapitalForecast(
            values=(500.0, 550.0, 605.0), years=(2026, 2027, 2028)
        ),
        taxes=TaxForecast(values=(0.25, 0.25, 0.25), years=(2026, 2027, 2028)),
        terminal_growth=TerminalGrowthForecast(rate=0.03, confidence=ConfidenceLevel.HIGH),
        confidence=ForecastConfidence(score=92.5, level=ConfidenceLevel.HIGH),
        assumptions=ForecastAssumption(
            revenue_growth_rate=0.10,
            ebitda_margin=0.22,
            tax_rate=0.25,
            capex_pct_revenue=0.05,
            working_capital_pct_revenue=0.10,
            metadata={"analyst": "Quant Core", "version": "v5.1.0-alpha.1"},
        ),
    )

    print(f"Scenario Name : {scenario.scenario_name}")
    print(f"Method        : {scenario.method.value}")
    print(f"Revenue Stream: {scenario.revenue.values}")

    # Test serialization round-trip
    payload = scenario.to_dict()
    restored = ForecastScenario.from_dict(payload)
    print(f"Serialization Equality Check Passed: {scenario == restored}")


if __name__ == "__main__":
    main()
