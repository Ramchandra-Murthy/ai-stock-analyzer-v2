from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ValuationMethod(StrEnum):
    DCF = "DCF"
    NAV = "NAV"
    SOTP = "SOTP"
    MARKET = "MARKET"
    BOOK_VALUE = "BOOK_VALUE"


class ValuationStatus(StrEnum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PENDING = "PENDING"


@dataclass(slots=True)
class ValuationResult:
    """Standardized valuation result shared by all service engines."""

    method: ValuationMethod
    entity_name: str = ""
    valuation_status: ValuationStatus = ValuationStatus.SUCCESS
    enterprise_value: float = 0.0
    equity_value: float = 0.0
    implied_share_price: float = 0.0
    diagnostics: dict[str, Any] = field(default_factory=dict)
    component_results: list[ValuationResult] = field(default_factory=list)
    raw_result: Any = None


@dataclass(slots=True)
class SOTPResult:
    """Aggregate valuation result produced by the SOTP engine."""

    enterprise_value: float
    equity_value: float
    implied_share_price: float
    net_debt: float
    holdco_discount_pct: float
    holdco_discount_amount: float
    component_results: list[ValuationResult] = field(default_factory=list)
