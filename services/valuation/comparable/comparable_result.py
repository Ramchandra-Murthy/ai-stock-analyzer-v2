from __future__ import annotations

"""
==========================================================
COMPARABLE COMPANY RESULT MODEL
Module  : comparable_result
Version : V1.0
==========================================================

Defines the standardized output of the Comparable Company
Analysis (CCA) valuation engine.

Returned by:
    • ComparableModel
    • ComparableEngine

Consumed by:
    • Valuation Dispatcher
    • SOTP Engine
    • Research Report
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ComparableResult:
    """
    Standard output from the Comparable Company valuation model.
    """

    company_name: str

    currency: str

    peer_count: int

    # Enterprise Value Estimates
    implied_enterprise_value_ev_sales: float

    implied_enterprise_value_ev_ebit: float

    implied_enterprise_value_ev_ebitda: float

    # Equity Value Estimates
    implied_equity_value_pe: float

    implied_equity_value_pb: float

    # Recommended Values
    recommended_enterprise_value: float

    recommended_equity_value: float

    implied_share_price: float

    # Applied Multiples
    median_ev_sales: float

    median_ev_ebit: float

    median_ev_ebitda: float

    median_pe: float

    median_pb: float

    # Statistical Diagnostics
    statistics: dict[str, Any] = field(default_factory=dict)

    # Validation
    validation_passed: bool = True

    warnings: list[str] = field(default_factory=list)

    diagnostics: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        """
        Lightweight reporting summary.
        """
        return {
            "company": self.company_name,
            "peer_count": self.peer_count,
            "enterprise_value": self.recommended_enterprise_value,
            "equity_value": self.recommended_equity_value,
            "share_price": self.implied_share_price,
        }
