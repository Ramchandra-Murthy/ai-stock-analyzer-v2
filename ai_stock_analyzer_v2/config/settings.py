from __future__ import annotations

"""
==========================================================
PLATFORM CONFIGURATION SETTINGS
Module  : config
Version : V3.0
==========================================================

Centralized system defaults, valuation parameters, and metadata.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ValuationSettings:
    """Default parameters for DCF, NAV, Comparable, and Market Value engines."""

    default_risk_free_rate: float = 0.070  # 7.0% (10-Yr Indian G-Sec)
    default_equity_risk_premium: float = 0.060  # 6.0% ERP
    default_terminal_growth_rate: float = 0.050  # 5.0% LT GDP growth
    default_conglomerate_discount: float = 0.15  # 15% holding discount
    default_tax_rate: float = 0.252  # 25.2% corporate tax rate


@dataclass(frozen=True)
class PlatformSettings:
    """System-wide configuration."""

    version: str = "3.0.0"
    environment: str = "development"
    log_level: str = "INFO"
    valuation: ValuationSettings = ValuationSettings()


settings = PlatformSettings()
