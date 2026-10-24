"""
==========================================================
Service Registry Enums
==========================================================
"""

from enum import StrEnum


class ServiceKey(StrEnum):
    RESEARCH = "research"
    FORECAST = "forecast"
    PORTFOLIO = "portfolio"
    MARKET = "market"
    VALUATION = "valuation"
    REPORT = "report"
