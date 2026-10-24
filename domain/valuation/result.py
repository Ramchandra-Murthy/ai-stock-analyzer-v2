from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ValuationMethod(StrEnum):
    DCF = "DCF"
    NAV = "NAV"
    SOTP = "SOTP"


class ValuationStatus(StrEnum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PENDING = "PENDING"


@dataclass
class ValuationResult:
    method: ValuationMethod
    enterprise_value: float = 0.0
    equity_value: float = 0.0
    implied_share_price: float = 0.0
    status: ValuationStatus = ValuationStatus.SUCCESS
    details: dict[str, Any] = field(default_factory=dict)
