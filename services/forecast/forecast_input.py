"""
==========================================================
FORECAST INPUT DOMAIN MODEL
Module  : services.forecast.forecast_input
Version : 5.1.0
Layer   : Services / Forecast / Input
==========================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from services.forecast.exceptions import ValuationError
from services.forecast.forecast_models import ForecastMethod


@dataclass(slots=True, frozen=True)
class HistoricalFinancials:
    revenue: tuple[float, ...]
    ebitda: tuple[float, ...] = field(default_factory=tuple)
    capex: tuple[float, ...] = field(default_factory=tuple)
    depreciation: tuple[float, ...] = field(default_factory=tuple)
    nwc: tuple[float, ...] = field(default_factory=tuple)


@dataclass(slots=True, frozen=True)
class ScenarioOverrides:
    revenue_growth_override: tuple[float, ...] | None = None
    margin_override: tuple[float, ...] | None = None


@dataclass(slots=True, frozen=True)
class ForecastInput:
    """Immutable forecast input supporting nested and legacy flat arguments."""

    symbol: str = "GENERIC"
    historical_data: HistoricalFinancials | None = None
    forecast_horizon: int = 5
    historical_revenues: tuple[float, ...] = field(default_factory=tuple)
    historical_ebits: tuple[float, ...] = field(default_factory=tuple)
    historical_nwc: tuple[float, ...] = field(default_factory=tuple)
    historical_capex: tuple[float, ...] = field(default_factory=tuple)
    historical_depreciation: tuple[float, ...] = field(default_factory=tuple)
    historical_pbt: tuple[float, ...] = field(default_factory=tuple)
    historical_tax: tuple[float, ...] = field(default_factory=tuple)
    forecast_years: int = 5
    method: ForecastMethod = ForecastMethod.CAGR
    management_guidance_revenue: tuple[float, ...] | None = None
    scenario_overrides: ScenarioOverrides | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str) or not self.symbol.strip():
            raise ValuationError("Ticker symbol cannot be empty.")

        revenues = self.historical_revenues
        if not revenues and self.historical_data and self.historical_data.revenue:
            revenues = self.historical_data.revenue
        revenues = tuple(revenues)

        horizon = self.forecast_years if self.forecast_years != 5 else self.forecast_horizon
        if not 1 <= horizon <= 10:
            raise ValuationError(f"Forecast horizon ({horizon}) must be between 1 and 10 years.")

        if len(revenues) < 2:
            raise ValuationError("Historical revenues must contain at least 2 periods.")

        series_fields = (
            "historical_ebits",
            "historical_nwc",
            "historical_capex",
            "historical_depreciation",
            "historical_pbt",
            "historical_tax",
        )
        normalized: dict[str, tuple[float, ...]] = {}
        for name in series_fields:
            values = tuple(getattr(self, name))
            if values and len(values) != len(revenues):
                raise ValuationError(
                    f"{name} length ({len(values)}) must match historical_revenues length ({len(revenues)})."
                )
            normalized[name] = values

        guidance = self.management_guidance_revenue
        if guidance is not None:
            guidance = tuple(guidance)
            if len(guidance) != horizon:
                raise ValuationError(
                    "management_guidance_revenue length must match forecast horizon."
                )
            object.__setattr__(self, "management_guidance_revenue", guidance)

        object.__setattr__(self, "historical_revenues", revenues)
        for name, values in normalized.items():
            object.__setattr__(self, name, values)
        object.__setattr__(self, "forecast_horizon", horizon)
        object.__setattr__(self, "forecast_years", horizon)

        if self.historical_data is None:
            object.__setattr__(
                self,
                "historical_data",
                HistoricalFinancials(
                    revenue=revenues,
                    ebitda=normalized["historical_ebits"],
                    capex=normalized["historical_capex"],
                    depreciation=normalized["historical_depreciation"],
                    nwc=normalized["historical_nwc"],
                ),
            )
