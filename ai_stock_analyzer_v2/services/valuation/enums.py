from enum import StrEnum


class ValuationMethod(StrEnum):
    """Supported valuation methodologies across the SOTP framework."""

    DCF = "DCF"
    EV_EBITDA = "EV/EBITDA"
    BOOK = "BOOK"
    NAV = "NAV"
    MARKET = "MARKET"


class ValuationStatus(StrEnum):
    """Lifecycle status of a segment or group valuation execution."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    UNSUPPORTED_METHOD = "UNSUPPORTED_METHOD"
