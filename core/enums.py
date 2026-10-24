from __future__ import annotations

"""
==========================================================
PLATFORM ENUMS
Module  : core.enums
Version : 4.0.0
==========================================================
"""

from enum import StrEnum


class Status(StrEnum):
    OK = "OK"
    UNAVAILABLE = "UNAVAILABLE"
    UNRESOLVED = "UNRESOLVED"
    FAILED = "FAILED"
    WARNING = "WARNING"


class ValuationMethod(StrEnum):
    DCF = "DCF"
    NAV = "NAV"
    COMPARABLE = "COMPARABLE"
    MARKET = "MARKET"
    BOOK = "BOOK"
    PRECEDENT = "PRECEDENT"
    MONTE_CARLO = "MONTE_CARLO"
    SOTP = "SOTP"


class AccountingStandard(StrEnum):
    IND_AS = "IND_AS"
    US_GAAP = "US_GAAP"
    IFRS = "IFRS"


class Currency(StrEnum):
    INR = "INR"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"


class MetricUnit(StrEnum):
    CRORES = "CR"
    MILLIONS = "M"
    BILLIONS = "B"
    RAW = "RAW"
