from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from services.forecast.models import ConfidenceLevel, ForecastMethod, ForecastPackage


@dataclass(frozen=True, slots=True, init=False)
class ForecastResult:
    """Encapsulates forecast execution output and the legacy result contract."""

    package: ForecastPackage | None
    execution_time_ms: float
    status: str
    error_message: str | None
    metadata: dict[str, Any]
    symbol: str
    forecast_horizon: int
    method_used: ForecastMethod
    confidence_level: ConfidenceLevel
    confidence_score: float
    revenue_forecast: Any
    margin_forecast: Any
    ebit_forecast: tuple[float, ...]
    capex_forecast: tuple[float, ...]

    def __init__(
        self,
        package: ForecastPackage | None = None,
        execution_time_ms: float = 0.0,
        status: str = "SUCCESS",
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
        *,
        symbol: str | None = None,
        forecast_horizon: int | None = None,
        method_used: ForecastMethod | None = None,
        confidence_level: ConfidenceLevel | None = None,
        confidence_score: float | None = None,
        revenue_forecast: Any = None,
        margin_forecast: Any = None,
        ebit_forecast: tuple[float, ...] = (),
        capex_forecast: tuple[float, ...] = (),
    ) -> None:
        legacy = package is None and any(
            value is not None
            for value in (
                symbol,
                forecast_horizon,
                method_used,
                confidence_level,
                confidence_score,
                revenue_forecast,
                margin_forecast,
            )
        )
        if legacy:
            object.__setattr__(self, "package", None)
            object.__setattr__(self, "symbol", symbol or "")
            object.__setattr__(self, "forecast_horizon", int(forecast_horizon or 0))
            object.__setattr__(
                self, "method_used", ForecastMethod(method_used or ForecastMethod.CAGR)
            )
            object.__setattr__(
                self,
                "confidence_level",
                ConfidenceLevel(confidence_level or ConfidenceLevel.MEDIUM),
            )
            object.__setattr__(self, "confidence_score", float(confidence_score or 0.0))
            object.__setattr__(self, "revenue_forecast", revenue_forecast)
            object.__setattr__(self, "margin_forecast", margin_forecast)
            object.__setattr__(self, "ebit_forecast", tuple(float(v) for v in ebit_forecast))
            object.__setattr__(self, "capex_forecast", tuple(float(v) for v in capex_forecast))
        else:
            object.__setattr__(self, "package", package)
            object.__setattr__(self, "symbol", package.ticker if package else "")
            object.__setattr__(self, "forecast_horizon", len(package.years) if package else 0)
            object.__setattr__(self, "method_used", ForecastMethod.CAGR)
            object.__setattr__(self, "confidence_level", ConfidenceLevel.MEDIUM)
            object.__setattr__(self, "confidence_score", 0.0)
            object.__setattr__(self, "revenue_forecast", None)
            object.__setattr__(self, "margin_forecast", None)
            object.__setattr__(self, "ebit_forecast", package.net_income.values if package else ())
            object.__setattr__(self, "capex_forecast", package.capex.values if package else ())
        object.__setattr__(self, "execution_time_ms", float(execution_time_ms))
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "error_message", error_message)
        object.__setattr__(self, "metadata", dict(metadata or {}))

    def to_dict(self) -> dict[str, Any]:
        if self.package is not None:
            return {
                "package": self.package.to_dict(),
                "execution_time_ms": self.execution_time_ms,
                "status": self.status,
                "error_message": self.error_message,
                "metadata": dict(self.metadata),
                "symbol": self.symbol,
                "forecast_horizon": self.forecast_horizon,
                "method_used": self.method_used.value.lower(),
                "confidence_level": self.confidence_level.value.lower(),
                "confidence_score": self.confidence_score,
                "revenue_forecast": None,
                "margin_forecast": None,
                "ebit_forecast": list(self.ebit_forecast),
                "capex_forecast": list(self.capex_forecast),
            }
        return {
            "symbol": self.symbol,
            "forecast_horizon": self.forecast_horizon,
            "method_used": self.method_used.value.lower(),
            "confidence_level": self.confidence_level.value.lower(),
            "confidence_score": self.confidence_score,
            "revenue_forecast": (
                self.revenue_forecast.to_dict() if self.revenue_forecast is not None else None
            ),
            "margin_forecast": (
                self.margin_forecast.to_dict() if self.margin_forecast is not None else None
            ),
            "ebit_forecast": list(self.ebit_forecast),
            "capex_forecast": list(self.capex_forecast),
            "package": None,
            "execution_time_ms": self.execution_time_ms,
            "status": self.status,
            "error_message": self.error_message,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ForecastResult:
        package = ForecastPackage.from_dict(data["package"]) if data.get("package") else None
        from services.forecast.models import MarginForecast, RevenueForecast

        revenue = data.get("revenue_forecast")
        margin = data.get("margin_forecast")
        return cls(
            package=package,
            execution_time_ms=float(data.get("execution_time_ms", 0.0)),
            status=data.get("status", "SUCCESS"),
            error_message=data.get("error_message"),
            metadata=dict(data.get("metadata", {})),
            symbol=data.get("symbol"),
            forecast_horizon=data.get("forecast_horizon"),
            method_used=ForecastMethod(str(data.get("method_used", "CAGR")).upper()),
            confidence_level=ConfidenceLevel(str(data.get("confidence_level", "MEDIUM")).upper()),
            confidence_score=float(data.get("confidence_score", 0.0)),
            revenue_forecast=RevenueForecast.from_dict(revenue) if revenue else None,
            margin_forecast=MarginForecast.from_dict(margin) if margin else None,
            ebit_forecast=tuple(data.get("ebit_forecast", ())),
            capex_forecast=tuple(data.get("capex_forecast", ())),
        )
