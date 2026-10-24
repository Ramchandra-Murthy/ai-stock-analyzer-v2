from __future__ import annotations

from enum import StrEnum


class Currency(StrEnum):
    """Supported fiat currencies for institutional equity research."""

    INR = "INR"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
