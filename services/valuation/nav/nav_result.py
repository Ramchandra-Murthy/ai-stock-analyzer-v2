from __future__ import annotations

"""
==========================================================
NET ASSET VALUE (NAV) RESULT MODEL
Module  : nav_result
Version : V1.0
==========================================================

Defines the standardized output of the NAV valuation engine.

Returned by NAVModel and consumed by:
    • NAV Engine Adapter
    • Valuation Dispatcher
    • SOTP Engine
    • Target Price Service
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class NAVResult:
    """
    Standard NAV valuation result.
    """

    company_name: str

    currency: str

    # Asset Side
    gross_asset_value: float

    total_book_value: float

    total_fair_value_adjustment: float

    # Liability Side
    total_liabilities: float

    minority_interest: float

    # NAV
    net_asset_value: float

    adjusted_nav: float

    holding_company_discount_pct: float

    equity_value: float

    shares_outstanding: float

    implied_share_price: float

    # Diagnostics
    asset_count: int

    liability_count: int

    included_asset_count: int

    included_liability_count: int

    # Audit
    validation_passed: bool = True

    warnings: list[str] = field(default_factory=list)

    diagnostics: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        """
        Lightweight summary for reporting.
        """
        return {
            "company": self.company_name,
            "gross_asset_value": self.gross_asset_value,
            "total_liabilities": self.total_liabilities,
            "equity_value": self.equity_value,
            "share_price": self.implied_share_price,
        }
