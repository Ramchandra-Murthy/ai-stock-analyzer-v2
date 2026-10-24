"""Legacy ForecastService compatibility facade.

This module preserves the older forecast API used by the v5.1/epic tests while
reusing the current forecast engines and models where practical.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from core.exceptions import ValidationError
from services.forecast.algorithms.cagr import CAGRForecastEngine
from services.forecast.forecast_input import ForecastInput
from services.forecast.forecast_models import ScenarioType


@dataclass(frozen=True, slots=True)
class YearlyForecast:
    revenue: float
    ebit: float
    capex: float
    depreciation: float
    nwc: float
    tax: float
    fcf: float


@dataclass(frozen=True, slots=True)
class ScenarioForecast:
    symbol: str
    yearly_forecasts: tuple[YearlyForecast, ...]
    effective_tax_rate: float
    projected_fcfs: tuple[float, ...]
    projected_revenues: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class IntegratedForecast:
    projected_revenues: tuple[float, ...]
    projected_ebit_margins: tuple[float, ...]
    projected_nwc: tuple[float, ...]
    projected_capex: tuple[float, ...]


class ForecastService:
    def __init__(self) -> None:
        self._engine = CAGRForecastEngine()

    @staticmethod
    def _validate_series(
        name: str, values: list[float] | tuple[float, ...], min_len: int = 2
    ) -> tuple[float, ...]:
        normalized = tuple(float(v) for v in values)
        if len(normalized) < min_len:
            raise ValidationError(f"{name} must contain at least {min_len} periods.")
        if not all(isfinite(v) for v in normalized):
            raise ValidationError(f"{name} must contain only finite numbers.")
        return normalized

    def generate_full_forecast(
        self, forecast_input: ForecastInput
    ) -> dict[ScenarioType, ScenarioForecast]:
        revenues = self._validate_series("historical_revenues", forecast_input.historical_revenues)
        ebits = self._validate_series("historical_ebits", forecast_input.historical_ebits)
        nwc = self._validate_series("historical_nwc", forecast_input.historical_nwc)
        capex = self._validate_series("historical_capex", forecast_input.historical_capex)
        depreciation = tuple(float(v) for v in forecast_input.historical_depreciation)
        pbt = tuple(float(v) for v in forecast_input.historical_pbt)
        tax = tuple(float(v) for v in forecast_input.historical_tax)
        periods = int(forecast_input.forecast_years)
        if periods < 1:
            raise ValidationError("forecast_years must be at least 1.")

        def scenario(multiplier: float, name: ScenarioType) -> ScenarioForecast:
            base_growth = (revenues[-1] / revenues[0]) ** (1.0 / (len(revenues) - 1)) - 1.0
            growth = base_growth * multiplier
            projected_revenues: list[float] = []
            last = revenues[-1]
            for _ in range(periods):
                last *= 1.0 + growth
                projected_revenues.append(last)

            ebit_margin = ebits[-1] / revenues[-1] if revenues[-1] else 0.0
            projected_fcfs: list[float] = []
            yearly: list[YearlyForecast] = []
            tax_rate = (tax[-1] / pbt[-1]) if tax and pbt and pbt[-1] else 0.25
            margin = max(0.0, min(1.0, ebit_margin))
            capex_ratio = abs(capex[-1] / revenues[-1]) if revenues[-1] else 0.0
            nwc_ratio = nwc[-1] / revenues[-1] if revenues[-1] else 0.0
            dep_ratio = (depreciation[-1] / revenues[-1]) if depreciation and revenues[-1] else 0.0
            previous_nwc = nwc[-1]

            for revenue in projected_revenues:
                ebit = revenue * margin
                projected_capex = revenue * capex_ratio
                projected_dep = revenue * dep_ratio
                projected_nwc = revenue * nwc_ratio
                delta_nwc = projected_nwc - previous_nwc
                fcf = ebit * (1.0 - tax_rate) + projected_dep - projected_capex - delta_nwc
                projected_fcfs.append(fcf)
                yearly.append(
                    YearlyForecast(
                        revenue, ebit, projected_capex, projected_dep, projected_nwc, tax_rate, fcf
                    )
                )
                previous_nwc = projected_nwc

            return ScenarioForecast(
                symbol=forecast_input.symbol,
                yearly_forecasts=tuple(yearly),
                effective_tax_rate=tax_rate,
                projected_fcfs=tuple(projected_fcfs),
                projected_revenues=tuple(projected_revenues),
            )

        return {
            ScenarioType.BASE: scenario(1.0, ScenarioType.BASE),
            ScenarioType.BULL: scenario(1.20, ScenarioType.BULL),
            ScenarioType.BEAR: scenario(0.80, ScenarioType.BEAR),
        }

    def build_forecast(
        self,
        historical_revenues: list[float] | tuple[float, ...],
        historical_ebits: list[float] | tuple[float, ...],
        historical_nwc: list[float] | tuple[float, ...],
        historical_capex: list[float] | tuple[float, ...],
        forecast_years: int,
    ) -> IntegratedForecast:
        revenues = self._validate_series("historical_revenues", historical_revenues)
        ebits = self._validate_series("historical_ebits", historical_ebits)
        nwc = self._validate_series("historical_nwc", historical_nwc)
        capex = tuple(float(v) for v in historical_capex)
        if len(ebits) != len(revenues) or len(nwc) != len(revenues) or len(capex) != len(revenues):
            raise ValidationError("Historical series must have matching lengths.")
        if forecast_years < 1:
            raise ValidationError("forecast_years must be at least 1.")

        projected_revenues = self._engine.calculate(revenues, forecast_years)
        margin = ebits[-1] / revenues[-1] if revenues[-1] else 0.0
        nwc_ratio = nwc[-1] / revenues[-1] if revenues[-1] else 0.0
        capex_ratio = capex[-1] / revenues[-1] if revenues[-1] else 0.0
        return IntegratedForecast(
            projected_revenues=projected_revenues,
            projected_ebit_margins=tuple(margin for _ in projected_revenues),
            projected_nwc=tuple(r * nwc_ratio for r in projected_revenues),
            projected_capex=tuple(r * capex_ratio for r in projected_revenues),
        )
