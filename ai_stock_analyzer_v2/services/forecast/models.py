from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, ClassVar

from services.forecast.exceptions import ForecastValidationError


class ForecastMethod(StrEnum):
    CAGR = "CAGR"
    LINEAR_REGRESSION = "LINEAR_REGRESSION"
    ROLLING_AVERAGE = "ROLLING_AVERAGE"
    MANAGEMENT_GUIDANCE = "MANAGEMENT_GUIDANCE"
    HISTORICAL_MEAN = "HISTORICAL_MEAN"


class ConfidenceLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True, slots=True)
class ForecastLineItem:
    name: str
    values: tuple[float, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "values": list(self.values)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ForecastLineItem:
        return cls(name=data["name"], values=tuple(data["values"]))


@dataclass(frozen=True, slots=True)
class ForecastPackage:
    ticker: str
    years: tuple[int, ...]
    revenue: ForecastLineItem
    net_income: ForecastLineItem
    capex: ForecastLineItem
    depreciation: ForecastLineItem
    working_capital: ForecastLineItem
    tax_rate: ForecastLineItem
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "years": list(self.years),
            "revenue": self.revenue.to_dict(),
            "net_income": self.net_income.to_dict(),
            "capex": self.capex.to_dict(),
            "depreciation": self.depreciation.to_dict(),
            "working_capital": self.working_capital.to_dict(),
            "tax_rate": self.tax_rate.to_dict(),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ForecastPackage:
        return cls(
            ticker=data["ticker"],
            years=tuple(data["years"]),
            revenue=ForecastLineItem.from_dict(data["revenue"]),
            net_income=ForecastLineItem.from_dict(data["net_income"]),
            capex=ForecastLineItem.from_dict(data["capex"]),
            depreciation=ForecastLineItem.from_dict(data["depreciation"]),
            working_capital=ForecastLineItem.from_dict(data["working_capital"]),
            tax_rate=ForecastLineItem.from_dict(data["tax_rate"]),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True, init=False)
class _ForecastSeries:
    values: tuple[float, ...]
    years: tuple[int, ...]
    historical: tuple[float, ...]
    projected: tuple[float, ...]
    method: ForecastMethod
    confidence: ConfidenceLevel
    growth_rates: tuple[float, ...]
    _kind: ClassVar[str] = "forecast"

    def __init__(
        self,
        values: tuple[float, ...] = (),
        years: tuple[int, ...] = (),
        *,
        historical: tuple[float, ...] | None = None,
        projected: tuple[float, ...] | None = None,
        method: ForecastMethod = ForecastMethod.CAGR,
        confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
        growth_rates: tuple[float, ...] = (),
    ) -> None:
        has_legacy = historical is not None or projected is not None
        if has_legacy:
            hist = tuple(float(value) for value in (historical or ()))
            proj = tuple(float(value) for value in (projected or ()))
            vals = proj
            yrs = tuple(range(1, len(proj) + 1))
        else:
            hist = ()
            proj = tuple(float(value) for value in values)
            vals = proj
            yrs = tuple(int(year) for year in years)
            if not yrs and proj:
                yrs = tuple(range(1, len(proj) + 1))
        if len(vals) != len(yrs):
            raise ForecastValidationError("values and years must have the same length")
        object.__setattr__(self, "values", vals)
        object.__setattr__(self, "years", yrs)
        object.__setattr__(self, "historical", hist)
        object.__setattr__(self, "projected", proj)
        object.__setattr__(self, "method", ForecastMethod(method))
        object.__setattr__(self, "confidence", ConfidenceLevel(confidence))
        object.__setattr__(self, "growth_rates", tuple(float(value) for value in growth_rates))

    def to_dict(self) -> dict[str, Any]:
        return {
            "values": list(self.values),
            "years": list(self.years),
            "historical": list(self.historical),
            "projected": list(self.projected),
            "method": self.method.value.lower(),
            "confidence": self.confidence.value.lower(),
            "growth_rates": list(self.growth_rates),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> _ForecastSeries:
        historical = tuple(data.get("historical", ()))
        projected = tuple(data.get("projected", data.get("values", ())))
        years = tuple(data.get("years", ()))
        method = ForecastMethod(str(data.get("method", "CAGR")).upper())
        confidence = ConfidenceLevel(str(data.get("confidence", "MEDIUM")).upper())
        growth_rates = tuple(data.get("growth_rates", ()))
        if historical:
            return cls(
                historical=historical,
                projected=projected,
                method=method,
                confidence=confidence,
                growth_rates=growth_rates,
            )
        return cls(
            values=tuple(data.get("values", projected)),
            years=years,
            method=method,
            confidence=confidence,
            growth_rates=growth_rates,
        )


@dataclass(frozen=True, slots=True, init=False)
class RevenueForecast(_ForecastSeries):
    pass


@dataclass(frozen=True, slots=True, init=False)
class MarginForecast(_ForecastSeries):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if any(value < 0.0 or value > 1.0 for value in self.values):
            raise ForecastValidationError("margin values must be between 0 and 1")


@dataclass(frozen=True, slots=True, init=False)
class CapexForecast(_ForecastSeries):
    pass


@dataclass(frozen=True, slots=True, init=False)
class DepreciationForecast(_ForecastSeries):
    pass


@dataclass(frozen=True, slots=True, init=False)
class WorkingCapitalForecast(_ForecastSeries):
    @property
    def delta(self) -> tuple[float, ...]:
        if not self.projected:
            return ()
        previous = self.historical[-1] if self.historical else 0.0
        deltas: list[float] = []
        for value in self.projected:
            deltas.append(float(value - previous))
            previous = value
        return tuple(deltas)


@dataclass(frozen=True, slots=True, init=False)
class TaxForecast(_ForecastSeries):
    pass


@dataclass(frozen=True, slots=True)
class TerminalGrowthForecast:
    rate: float
    confidence: ConfidenceLevel

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", ConfidenceLevel(self.confidence))
        if not 0.0 <= self.rate < 1.0:
            raise ForecastValidationError("terminal growth rate must be in [0, 1)")

    def to_dict(self) -> dict[str, Any]:
        return {"rate": self.rate, "confidence": self.confidence.value}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TerminalGrowthForecast:
        return cls(rate=float(data["rate"]), confidence=ConfidenceLevel(data["confidence"]))


@dataclass(frozen=True, slots=True)
class ForecastConfidence:
    score: float
    level: ConfidenceLevel

    def __post_init__(self) -> None:
        object.__setattr__(self, "level", ConfidenceLevel(self.level))
        if not 0.0 <= self.score <= 100.0:
            raise ForecastValidationError("confidence score must be between 0 and 100")

    def to_dict(self) -> dict[str, Any]:
        return {"score": self.score, "level": self.level.value}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ForecastConfidence:
        return cls(score=float(data["score"]), level=ConfidenceLevel(data["level"]))


@dataclass(frozen=True, slots=True, init=False)
class ForecastAssumption:
    revenue_growth_rate: float
    ebitda_margin: float
    tax_rate: float
    capex_pct_revenue: float
    working_capital_pct_revenue: float
    metadata: dict[str, Any]

    def __init__(
        self,
        revenue_growth_rate: float,
        ebitda_margin: float,
        tax_rate: float,
        capex_pct_revenue: float,
        working_capital_pct_revenue: float,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        object.__setattr__(self, "revenue_growth_rate", float(revenue_growth_rate))
        object.__setattr__(self, "ebitda_margin", float(ebitda_margin))
        object.__setattr__(self, "tax_rate", float(tax_rate))
        object.__setattr__(self, "capex_pct_revenue", float(capex_pct_revenue))
        object.__setattr__(self, "working_capital_pct_revenue", float(working_capital_pct_revenue))
        object.__setattr__(self, "metadata", dict(metadata or {}))

    def to_dict(self) -> dict[str, Any]:
        return {
            "revenue_growth_rate": self.revenue_growth_rate,
            "ebitda_margin": self.ebitda_margin,
            "tax_rate": self.tax_rate,
            "capex_pct_revenue": self.capex_pct_revenue,
            "working_capital_pct_revenue": self.working_capital_pct_revenue,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ForecastAssumption:
        return cls(
            **{
                key: float(data[key])
                for key in (
                    "revenue_growth_rate",
                    "ebitda_margin",
                    "tax_rate",
                    "capex_pct_revenue",
                    "working_capital_pct_revenue",
                )
            },
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True, init=False)
class ForecastScenario:
    scenario_name: str
    method: ForecastMethod
    revenue: RevenueForecast
    margins: MarginForecast
    capex: CapexForecast
    depreciation: DepreciationForecast
    working_capital: WorkingCapitalForecast
    taxes: TaxForecast
    terminal_growth: TerminalGrowthForecast
    confidence: ForecastConfidence
    assumptions: ForecastAssumption
    probability: float

    def __init__(
        self,
        scenario_name: str,
        method: ForecastMethod,
        revenue: RevenueForecast | None = None,
        margins: MarginForecast | None = None,
        capex: CapexForecast | None = None,
        depreciation: DepreciationForecast | None = None,
        working_capital: WorkingCapitalForecast | None = None,
        taxes: TaxForecast | None = None,
        terminal_growth: TerminalGrowthForecast | None = None,
        confidence: ForecastConfidence | None = None,
        assumptions: ForecastAssumption | None = None,
        probability: float = 1.0,
        **legacy: Any,
    ) -> None:
        revenue = revenue or legacy.pop("revenue_forecast", None)
        margins = margins or legacy.pop("margin_forecast", None)
        capex = capex or legacy.pop("capex_forecast", None)
        taxes = taxes or legacy.pop("tax_forecast", None)
        terminal_growth = terminal_growth or legacy.pop("terminal_growth", None)
        probability = float(legacy.pop("probability", probability))
        if legacy:
            raise TypeError(f"Unexpected ForecastScenario arguments: {', '.join(legacy)}")
        if revenue is None or margins is None or capex is None or taxes is None:
            raise TypeError("ForecastScenario requires revenue, margins, capex, and taxes")
        depreciation = depreciation or DepreciationForecast()
        working_capital = working_capital or WorkingCapitalForecast()
        terminal_growth = terminal_growth or TerminalGrowthForecast(0.03, ConfidenceLevel.MEDIUM)
        confidence = confidence or ForecastConfidence(0.0, ConfidenceLevel.MEDIUM)
        assumptions = assumptions or ForecastAssumption(0.0, 0.0, 0.25, 0.0, 0.0)
        object.__setattr__(self, "scenario_name", scenario_name)
        object.__setattr__(self, "method", ForecastMethod(method))
        object.__setattr__(self, "revenue", revenue)
        object.__setattr__(self, "margins", margins)
        object.__setattr__(self, "capex", capex)
        object.__setattr__(self, "depreciation", depreciation)
        object.__setattr__(self, "working_capital", working_capital)
        object.__setattr__(self, "taxes", taxes)
        object.__setattr__(self, "terminal_growth", terminal_growth)
        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(self, "assumptions", assumptions)
        if not 0.0 <= probability <= 1.0:
            raise ForecastValidationError("scenario probability must be between 0 and 1")
        object.__setattr__(self, "probability", probability)

    @property
    def revenue_forecast(self) -> RevenueForecast:
        return self.revenue

    @property
    def margin_forecast(self) -> MarginForecast:
        return self.margins

    @property
    def capex_forecast(self) -> CapexForecast:
        return self.capex

    @property
    def tax_forecast(self) -> TaxForecast:
        return self.taxes

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_name": self.scenario_name,
            "method": self.method.value,
            "probability": self.probability,
            "revenue": self.revenue.to_dict(),
            "margins": self.margins.to_dict(),
            "capex": self.capex.to_dict(),
            "depreciation": self.depreciation.to_dict(),
            "working_capital": self.working_capital.to_dict(),
            "taxes": self.taxes.to_dict(),
            "terminal_growth": self.terminal_growth.to_dict(),
            "confidence": self.confidence.to_dict(),
            "assumptions": self.assumptions.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ForecastScenario:
        return cls(
            scenario_name=data["scenario_name"],
            method=ForecastMethod(data["method"]),
            probability=float(data.get("probability", 1.0)),
            revenue=RevenueForecast.from_dict(data["revenue"]),
            margins=MarginForecast.from_dict(data["margins"]),
            capex=CapexForecast.from_dict(data["capex"]),
            depreciation=DepreciationForecast.from_dict(data["depreciation"]),
            working_capital=WorkingCapitalForecast.from_dict(data["working_capital"]),
            taxes=TaxForecast.from_dict(data["taxes"]),
            terminal_growth=TerminalGrowthForecast.from_dict(data["terminal_growth"]),
            confidence=ForecastConfidence.from_dict(data["confidence"]),
            assumptions=ForecastAssumption.from_dict(data["assumptions"]),
        )
