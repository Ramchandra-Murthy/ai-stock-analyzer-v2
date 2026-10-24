from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ForecastInput:
    """Input payload containing historical financials and configuration for forecasting."""

    ticker: str
    historical_years: tuple[int, ...]
    historical_revenue: tuple[float, ...]
    historical_margins: tuple[float, ...]
    historical_capex: tuple[float, ...]
    historical_depreciation: tuple[float, ...]
    historical_working_capital: tuple[float, ...]
    historical_taxes: tuple[float, ...]
    forecast_years: tuple[int, ...]
    custom_growth_rate: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
