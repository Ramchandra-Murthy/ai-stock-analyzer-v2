from __future__ import annotations

from enum import StrEnum


class ExchangeCode(StrEnum):
    """Standardized exchange identifiers."""

    NSE = "NSE"
    BSE = "BSE"
    NYSE = "NYSE"
    NASDAQ = "NASDAQ"
    LSE = "LSE"

    def to_dict(self) -> str:
        return self.value
