"""
==========================================================
EQUITY VALUATION PLATFORM v5.2
Module  : services.wacc.wacc_models
Layer   : Services / WACC / Domain Models
Summary : Core domain models for Weighted Average Cost of Capital (WACC),
          Cost of Equity (CAPM), Cost of Debt, and Beta adjustments.
==========================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True, frozen=True)
class CAPMInput:
    """Input parameters for Capital Asset Pricing Model (CAPM)."""

    risk_free_rate: float  # e.g., 0.071 (7.1% 10-Yr Govt Bond)
    equity_risk_premium: float  # e.g., 0.055 (5.5% ERP)
    beta: float  # Levered Beta (e.g., 1.15)
    size_premium: float = 0.0  # Optional size adjustment factor

    def __post_init__(self) -> None:
        if not (0.0 <= self.risk_free_rate <= 0.30):
            raise ValueError("Risk-free rate must be between 0% and 30%.")
        if not (0.0 <= self.equity_risk_premium <= 0.20):
            raise ValueError("Equity risk premium must be between 0% and 20%.")
        if self.beta < 0.0:
            raise ValueError("Beta must be non-negative.")


@dataclass(slots=True, frozen=True)
class BetaAdjustmentInput:
    """Input payload for Hamada unlevering/relevering calculation."""

    levered_beta: float
    debt_to_equity_ratio: float
    tax_rate: float

    def __post_init__(self) -> None:
        if self.levered_beta < 0.0:
            raise ValueError("Levered beta must be non-negative.")
        if self.debt_to_equity_ratio < 0.0:
            raise ValueError("Debt-to-Equity ratio cannot be negative.")
        if not (0.0 <= self.tax_rate <= 0.60):
            raise ValueError("Tax rate must be between 0% and 60%.")


@dataclass(slots=True, frozen=True)
class WACCInput:
    """Input payload for Weighted Average Cost of Capital computation."""

    symbol: str
    market_cap: float  # Market Value of Equity (E)
    total_debt: float  # Market Value of Debt (D)
    cost_of_equity: float  # Re
    cost_of_debt: float  # Rd
    tax_rate: float  # Tc (Corporate tax rate)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError("Symbol cannot be empty.")
        if self.market_cap <= 0.0:
            raise ValueError("Market capitalisation must be strictly positive.")
        if self.total_debt < 0.0:
            raise ValueError("Total debt cannot be negative.")
        if not (0.0 <= self.tax_rate <= 0.60):
            raise ValueError("Tax rate must be between 0% and 60%.")


@dataclass(slots=True, frozen=True)
class WACCResult:
    """Output payload from WACC calculation engine."""

    symbol: str
    wacc: float
    cost_of_equity: float
    cost_of_debt_after_tax: float
    equity_weight: float
    debt_weight: float

    @property
    def discount_rate(self) -> float:
        return self.wacc
