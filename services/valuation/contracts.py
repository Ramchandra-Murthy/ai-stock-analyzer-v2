from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from services.valuation.enums import ValuationMethod, ValuationStatus


@dataclass(slots=True)
class SOTPSegmentInput:
    """Strongly-typed input contract for individual SOTP operating segments."""

    segment_name: str
    valuation_method: ValuationMethod = ValuationMethod.DCF

    # Financial Base Drivers
    last_historical_revenue: float = 1000.0
    revenue_growth_rates: list[float] = field(
        default_factory=lambda: [0.10, 0.08, 0.07, 0.06, 0.05]
    )
    ebit_margin_forecast: list[float] = field(
        default_factory=lambda: [0.18, 0.18, 0.19, 0.19, 0.20]
    )
    dna_pct_rev: list[float] = field(default_factory=lambda: [0.03, 0.03, 0.03, 0.03, 0.03])
    capex_pct_rev: list[float] = field(default_factory=lambda: [0.04, 0.04, 0.04, 0.04, 0.04])
    nwc_pct_rev: list[float] = field(default_factory=lambda: [0.02, 0.02, 0.02, 0.02, 0.02])

    # Capital Structure & Discount Parameters
    tax_rate: float = 0.25
    equity_weight: float = 0.80
    debt_weight: float = 0.20
    cost_of_equity: float = 0.12
    cost_of_debt_post_tax: float = 0.05
    terminal_growth_rate: float = 0.04

    # Segment Net Debt Bridge
    segment_debt: float = 0.0
    segment_cash: float = 0.0
    shares_outstanding: float = 100.0
    currency: str = "INR"

    def validate_early(self) -> None:
        """Fails fast with segment-specific context before invoking lower engines."""
        if not self.segment_name or not self.segment_name.strip():
            raise ValueError("Segment name cannot be empty.")
        if self.last_historical_revenue <= 0:
            raise ValueError(f"[{self.segment_name}] last_historical_revenue must be > 0.")
        if not self.revenue_growth_rates:
            raise ValueError(f"[{self.segment_name}] revenue_growth_rates array cannot be empty.")


@dataclass(slots=True)
class SOTPSegmentResult:
    """Standardized result output for a processed segment."""

    segment_name: str
    valuation_method: ValuationMethod
    valuation_status: ValuationStatus

    enterprise_value: float = 0.0
    equity_value: float = 0.0
    implied_share_price: float = 0.0

    # Extended Audit & Report Fields
    wacc: float | None = None
    terminal_value_pct: float | None = None
    forecast_years: int | None = None
    currency: str = "INR"
    audit_details: Any | None = None
    error_message: str | None = None
