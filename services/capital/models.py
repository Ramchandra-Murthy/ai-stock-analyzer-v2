"""
==========================================================
CAPITAL COST DOMAIN MODELS MODULE
Module  : services.capital.models
Layer   : Services / Capital / Domain Models
==========================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True, frozen=True)
class CapitalStructure:
    """Immutable representation of a firm's capital weighting mix."""

    total_debt: float
    total_equity: float
    preferred_stock: float = 0.0

    @property
    def total_capital(self) -> float:
        return self.total_debt + self.total_equity + self.preferred_stock

    @property
    def debt_weight(self) -> float:
        tc = self.total_capital
        return self.total_debt / tc if tc > 0 else 0.0

    @property
    def equity_weight(self) -> float:
        tc = self.total_capital
        return self.total_equity / tc if tc > 0 else 0.0


@dataclass(slots=True, frozen=True)
class CostOfEquityResult:
    """Immutable container for CAPM-based Cost of Equity calculations."""

    risk_free_rate: float
    beta: float
    equity_risk_premium: float
    cost_of_equity: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_free_rate": self.risk_free_rate,
            "beta": self.beta,
            "equity_risk_premium": self.equity_risk_premium,
            "cost_of_equity": self.cost_of_equity,
        }


@dataclass(slots=True, frozen=True)
class CostOfDebtResult:
    """Immutable container for pre-tax and after-tax Cost of Debt calculations."""

    pre_tax_cost_of_debt: float
    effective_tax_rate: float
    after_tax_cost_of_debt: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "pre_tax_cost_of_debt": self.pre_tax_cost_of_debt,
            "effective_tax_rate": self.effective_tax_rate,
            "after_tax_cost_of_debt": self.after_tax_cost_of_debt,
        }


@dataclass(slots=True, frozen=True)
class WACCResult:
    """Immutable container representing the final WACC output and component breakdowns."""

    symbol: str
    capital_structure: CapitalStructure
    cost_of_equity: CostOfEquityResult
    cost_of_debt: CostOfDebtResult
    wacc: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "capital_structure": {
                "total_debt": self.capital_structure.total_debt,
                "total_equity": self.capital_structure.total_equity,
                "debt_weight": self.capital_structure.debt_weight,
                "equity_weight": self.capital_structure.equity_weight,
            },
            "cost_of_equity": self.cost_of_equity.to_dict(),
            "cost_of_debt": self.cost_of_debt.to_dict(),
            "wacc": self.wacc,
            "metadata": self.metadata,
        }
