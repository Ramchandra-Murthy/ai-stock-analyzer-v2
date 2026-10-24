from __future__ import annotations

from enum import StrEnum


class AssetClass(StrEnum):
    """Broad asset classes for institutional research."""

    EQUITY = "EQUITY"
    FIXED_INCOME = "FIXED_INCOME"
    COMMODITY = "COMMODITY"
    FOREX = "FOREX"
    CRYPTO = "CRYPTO"


class MarketExchange(StrEnum):
    """Major stock exchanges."""

    NSE = "NSE"
    BSE = "BSE"
    NYSE = "NYSE"
    NASDAQ = "NASDAQ"
    LSE = "LSE"


class ExchangeCode(StrEnum):
    """Exchange code representation."""

    NSE = "NSE"
    BSE = "BSE"
    NYSE = "NYSE"
    NASDAQ = "NASDAQ"
    LSE = "LSE"


class FiscalQuarter(StrEnum):
    """Fiscal quarters."""

    Q1 = "Q1"
    Q2 = "Q2"
    Q3 = "Q3"
    Q4 = "Q4"


class Sector(StrEnum):
    """GICS or standard industry sectors."""

    TECHNOLOGY = "TECHNOLOGY"
    FINANCIALS = "FINANCIALS"
    ENERGY = "ENERGY"
    HEALTHCARE = "HEALTHCARE"
    CONSUMER_DISCRETIONARY = "CONSUMER_DISCRETIONARY"
    CONSUMER_STAPLES = "CONSUMER_STAPLES"
    INDUSTRIALS = "INDUSTRIALS"
    MATERIALS = "MATERIALS"
    UTILITIES = "UTILITIES"
    REAL_ESTATE = "REAL_ESTATE"
    COMMUNICATION_SERVICES = "COMMUNICATION_SERVICES"


class Industry(StrEnum):
    """Sub-industries."""

    SOFTWARE = "SOFTWARE"
    BANKS = "BANKS"
    PHARMACEUTICALS = "PHARMACEUTICALS"
    AUTOMOBILES = "AUTOMOBILES"
