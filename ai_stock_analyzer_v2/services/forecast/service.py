from __future__ import annotations

import time

from services.forecast.algorithms.base import BaseForecastAlgorithm
from services.forecast.algorithms.cagr import CAGRForecastEngine
from services.forecast.algorithms.linear_regression import LinearRegressionForecastEngine
from services.forecast.assumption_engine import AssumptionEngine
from services.forecast.exceptions import ForecastError
from services.forecast.input import ForecastInput
from services.forecast.models import (
    CapexForecast,
    ConfidenceLevel,
    DepreciationForecast,
    ForecastConfidence,
    ForecastLineItem,
    ForecastMethod,
    ForecastPackage,
    ForecastScenario,
    MarginForecast,
    RevenueForecast,
    TaxForecast,
    TerminalGrowthForecast,
    WorkingCapitalForecast,
)
from services.forecast.result import ForecastResult
from services.forecast.validation import ForecastValidator


class ForecastService:
    def __init__(self, algorithm: BaseForecastAlgorithm | None = None) -> None:
        self.algorithm = algorithm or CAGRForecastEngine()

    def execute(self, forecast_input: ForecastInput) -> ForecastResult:
        start_time = time.perf_counter()
        try:
            ForecastValidator.validate_input(forecast_input)
            years = forecast_input.forecast_years
            revenues = self.algorithm.calculate_revenue(forecast_input)
            margins = self.algorithm.calculate_margins(forecast_input)
            capex = self.algorithm.calculate_capex(forecast_input)
            depreciation = self.algorithm.calculate_depreciation(forecast_input)
            working_capital = self.algorithm.calculate_working_capital(forecast_input)
            taxes = self.algorithm.calculate_taxes(forecast_input)
            net_income = tuple(r * m for r, m in zip(revenues, margins, strict=False))
            package = ForecastPackage(
                ticker=forecast_input.ticker,
                years=years,
                revenue=ForecastLineItem("Revenue", revenues),
                net_income=ForecastLineItem("Net Income", net_income),
                capex=ForecastLineItem("Capital Expenditures", capex),
                depreciation=ForecastLineItem("Depreciation", depreciation),
                working_capital=ForecastLineItem("Working Capital", working_capital),
                tax_rate=ForecastLineItem("Tax Rate", taxes),
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return ForecastResult(
                package=package,
                execution_time_ms=round(elapsed_ms, 3),
                status="SUCCESS",
                metadata={"algorithm": self.algorithm.__class__.__name__},
            )
        except ForecastError as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            empty_item = ForecastLineItem("", ())
            pkg = ForecastPackage(
                ticker=forecast_input.ticker,
                years=(),
                revenue=empty_item,
                net_income=empty_item,
                capex=empty_item,
                depreciation=empty_item,
                working_capital=empty_item,
                tax_rate=empty_item,
            )
            return ForecastResult(
                package=pkg,
                execution_time_ms=round(elapsed_ms, 3),
                status="FAILED",
                error_message=str(e),
                metadata={"algorithm": self.algorithm.__class__.__name__},
            )

    def generate_revenue_forecast(
        self,
        historical: tuple[float, ...],
        periods: int,
        method: ForecastMethod = ForecastMethod.CAGR,
        confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
    ) -> RevenueForecast:
        algorithm = self._algorithm_for(method)
        projected = algorithm.calculate(historical, periods)
        growth_rates = tuple(
            ((projected[i] / historical[-1]) - 1.0) if historical and historical[-1] != 0 else 0.0
            for i in range(len(projected))
        )
        return RevenueForecast(
            historical=historical,
            projected=projected,
            method=method,
            confidence=confidence,
            growth_rates=growth_rates,
        )

    def generate_working_capital_forecast(
        self,
        historical: tuple[float, ...],
        periods: int,
        method: ForecastMethod = ForecastMethod.CAGR,
        confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
    ) -> WorkingCapitalForecast:
        algorithm = self._algorithm_for(method)
        projected = algorithm.calculate(historical, periods)
        return WorkingCapitalForecast(
            historical=historical,
            projected=projected,
            method=method,
            confidence=confidence,
        )

    def generate_scenario(
        self,
        scenario_name: str,
        probability: float,
        historical_revenue: tuple[float, ...],
        historical_margin: tuple[float, ...],
        historical_capex: tuple[float, ...],
        periods: int,
        method: ForecastMethod = ForecastMethod.CAGR,
    ) -> ForecastScenario:
        confidence = ConfidenceLevel.MEDIUM
        revenue = self.generate_revenue_forecast(historical_revenue, periods, method, confidence)
        margin_algorithm = self._algorithm_for(method)
        margins = tuple(
            max(0.0, min(1.0, value))
            for value in margin_algorithm.calculate(historical_margin, periods)
        )
        capex = CapexForecast(
            historical=historical_capex,
            projected=self._algorithm_for(method).calculate(historical_capex, periods),
            method=method,
            confidence=confidence,
        )
        tax_projected = tuple(0.25 for _ in range(periods))
        taxes = TaxForecast(
            historical=(), projected=tax_projected, method=method, confidence=confidence
        )
        assumptions = AssumptionEngine.derive_assumptions(
            historical_revenue, historical_margin, historical_capex, method
        )
        return ForecastScenario(
            scenario_name=scenario_name,
            method=method,
            probability=probability,
            revenue=revenue,
            margins=MarginForecast(
                historical=historical_margin,
                projected=margins,
                method=method,
                confidence=confidence,
            ),
            capex=capex,
            depreciation=DepreciationForecast(projected=(), method=method, confidence=confidence),
            working_capital=WorkingCapitalForecast(
                projected=(), method=method, confidence=confidence
            ),
            taxes=taxes,
            terminal_growth=TerminalGrowthForecast(0.03, ConfidenceLevel.HIGH),
            confidence=ForecastConfidence(85.0, ConfidenceLevel.HIGH),
            assumptions=assumptions,
        )

    @staticmethod
    def _algorithm_for(method: ForecastMethod) -> BaseForecastAlgorithm:
        if method == ForecastMethod.LINEAR_REGRESSION:
            return LinearRegressionForecastEngine()
        return CAGRForecastEngine()
