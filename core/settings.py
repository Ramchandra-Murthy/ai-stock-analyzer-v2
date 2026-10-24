from __future__ import annotations

"""
==========================================================
GLOBAL PLATFORM CONFIGURATION & DEFAULTS
Module  : core.settings
Version : 4.0.0
==========================================================
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DCFSettings:
    DEFAULT_TAX_RATE: float = 0.25
    DEFAULT_COST_OF_EQUITY: float = 0.12
    DEFAULT_COST_OF_DEBT_POST_TAX: float = 0.06
    DEFAULT_EQUITY_WEIGHT: float = 0.80
    DEFAULT_DEBT_WEIGHT: float = 0.20
    DEFAULT_TERMINAL_GROWTH: float = 0.03
    DEFAULT_FORECAST_YEARS: int = 5
    DEFAULT_REVENUE_GROWTH: float = 0.08
    DEFAULT_CAPEX_PCT_REV: float = 0.05
    DEFAULT_NWC_PCT_REV: float = 0.02


@dataclass(frozen=True)
class NAVSettings:
    DEFAULT_HOLDCO_DISCOUNT: float = 0.15


@dataclass(frozen=True)
class AccountingSettings:
    STRICT_BALANCE_SHEET_CHECK: bool = True
    BALANCE_SHEET_TOLERANCE: float = 1.0


@dataclass(frozen=True)
class PlatformSettings:
    ENV: str = "DEVELOPMENT"
    dcf: DCFSettings = DCFSettings()
    nav: NAVSettings = NAVSettings()
    accounting: AccountingSettings = AccountingSettings()


settings = PlatformSettings()
