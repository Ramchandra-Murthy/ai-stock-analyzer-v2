from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CapitalStructure:
    market_cap: float
    total_debt: float
    cash_and_equivalents: float

    @property
    def net_debt(self) -> float:
        return max(0.0, self.total_debt - self.cash_and_equivalents)

    @property
    def enterprise_value(self) -> float:
        return self.market_cap + self.net_debt

    @property
    def weight_equity(self) -> float:
        total = self.market_cap + self.total_debt
        return self.market_cap / total if total > 0 else 1.0

    @property
    def weight_debt(self) -> float:
        total = self.market_cap + self.total_debt
        return self.total_debt / total if total > 0 else 0.0


@dataclass(frozen=True, slots=True)
class WACCResult:
    cost_of_equity: float
    cost_of_debt_pre_tax: float
    cost_of_debt_post_tax: float
    weight_equity: float
    weight_debt: float
    effective_tax_rate: float
    wacc: float
