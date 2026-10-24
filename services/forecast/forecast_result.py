"""
==========================================================
EQUITY VALUATION PLATFORM v5.1
Module  : services.forecast.forecast_result
Layer   : Services / Forecast / Output Contracts
Summary : Aggregated immutable output container for complete company
          financial forecasts.
==========================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from services.forecast.forecast_models import (
    CapexForecast,
    DepreciationForecast,
    ForecastConfidence,
    ForecastScenario,
    MarginForecast,
    RevenueForecast,
    TaxForecast,
    TerminalGrowthForecast,
    WorkingCapitalForecast,
)


@dataclass(frozen=True, slots=True)
class YearlyFinancialForecast:
    """Individual annual forecast statement item."""

    year: int
    revenue: float
    margin: float
    ebit: float
    capex: float
    depreciation: float
    working_capital: float
    tax: float

    @property
    def free_cash_flow(self) -> float:
        """Calculates Free Cash Flow to Firm for the year."""
        nopat = self.ebit - self.tax
        return round(nopat + self.depreciation - self.capex - self.working_capital, 4)


@dataclass(frozen=True, slots=True)
class ForecastResult:
    """Master output contract containing complete financial projections for a valuation subject."""

    symbol: str
    revenue: RevenueForecast
    margin: MarginForecast
    capex: CapexForecast
    depreciation: DepreciationForecast
    working_capital: WorkingCapitalForecast
    tax: TaxForecast
    terminal_growth: TerminalGrowthForecast
    confidence: ForecastConfidence
    scenarios: tuple[ForecastScenario, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    # ----------------------------------------------------
    # Subservice Aliases & Compatibility Accessors
    # ----------------------------------------------------
    @property
    def revenue_forecast(self) -> RevenueForecast:
        return self.revenue

    @property
    def margin_forecast(self) -> MarginForecast:
        return self.margin

    @property
    def capex_forecast(self) -> CapexForecast:
        return self.capex

    @property
    def depreciation_forecast(self) -> DepreciationForecast:
        return self.depreciation

    @property
    def working_capital_forecast(self) -> WorkingCapitalForecast:
        return self.working_capital

    @property
    def tax_forecast(self) -> TaxForecast:
        return self.tax

    @property
    def forecast_years(self) -> int:
        """Returns projection horizon length."""
        return len(self.revenue.projected)

    # ----------------------------------------------------
    # Vector Property Accessors
    # ----------------------------------------------------
    @property
    def projected_revenues(self) -> tuple[float, ...]:
        """Direct accessor for projected revenue series."""
        return tuple(self.revenue.projected)

    @property
    def projected_ebit_margins(self) -> list[float]:
        """List accessor for projected EBIT margins matching legacy test expectations."""
        return [round(m, 4) for m in self.margin.projected]

    @property
    def projected_ebit(self) -> tuple[float, ...]:
        """Calculates projected EBIT series: Revenue * Margin."""
        return tuple(
            round(rev * margin, 4)
            for rev, margin in zip(self.revenue.projected, self.margin.projected, strict=False)
        )

    @property
    def projected_nopat(self) -> tuple[float, ...]:
        """Calculates projected Net Operating Profit After Tax (NOPAT): EBIT - Tax."""
        ebits = self.projected_ebit
        taxes = tuple(self.tax.projected)
        return tuple(round(ebit - tax, 4) for ebit, tax in zip(ebits, taxes, strict=False))

    @property
    def projected_fcff(self) -> tuple[float, ...]:
        """Calculates projected Free Cash Flow to Firm (FCFF): NOPAT + D&A - CapEx - Delta NWC."""
        nopats = self.projected_nopat
        deps = tuple(self.depreciation.projected)
        capex = tuple(self.capex.projected)
        delta_nwc = tuple(self.working_capital.delta_nwc)

        return tuple(
            round(nopat + dep - cap - dnwc, 4)
            for nopat, dep, cap, dnwc in zip(nopats, deps, capex, delta_nwc, strict=False)
        )

    @property
    def projected_fcfs(self) -> tuple[float, ...]:
        """Legacy alias accessor for projected FCFF."""
        return self.projected_fcff

    @property
    def yearly_forecasts(self) -> tuple[YearlyFinancialForecast, ...]:
        """Returns annual structured financial objects across the forecast horizon."""
        revs = tuple(self.revenue.projected)
        margins = tuple(self.margin.projected)
        ebits = self.projected_ebit
        capexs = tuple(self.capex.projected)
        deps = tuple(self.depreciation.projected)
        nwcs = tuple(self.working_capital.delta_nwc)
        taxes = tuple(self.tax.projected)

        yearly = []
        for year_idx in range(len(revs)):
            yearly.append(
                YearlyFinancialForecast(
                    year=year_idx + 1,
                    revenue=revs[year_idx],
                    margin=margins[year_idx] if year_idx < len(margins) else 0.0,
                    ebit=ebits[year_idx] if year_idx < len(ebits) else 0.0,
                    capex=capexs[year_idx] if year_idx < len(capexs) else 0.0,
                    depreciation=deps[year_idx] if year_idx < len(deps) else 0.0,
                    working_capital=nwcs[year_idx] if year_idx < len(nwcs) else 0.0,
                    tax=taxes[year_idx] if year_idx < len(taxes) else 0.0,
                )
            )
        return tuple(yearly)
