from __future__ import annotations

"""
==========================================================
NET ASSET VALUE (NAV) INPUT MODEL
Module  : nav_input
Version : V1.0
==========================================================

Defines immutable input contracts for the NAV valuation
engine.
"""

from dataclasses import dataclass, field

# ==========================================================
# Asset
# ==========================================================


@dataclass(slots=True)
class NAVAsset:
    """
    Represents a single economic asset.
    """

    name: str

    category: str

    book_value: float

    fair_value: float

    ownership_pct: float = 100.0

    include_in_nav: bool = True

    notes: str = ""


# ==========================================================
# Liability
# ==========================================================


@dataclass(slots=True)
class NAVLiability:
    """
    Represents a liability deducted from asset value.
    """

    name: str

    category: str

    amount: float

    include_in_nav: bool = True

    notes: str = ""


# ==========================================================
# NAV Input
# ==========================================================


@dataclass(slots=True)
class NAVInput:
    """
    Master input object consumed by the NAV engine.
    """

    company_name: str

    currency: str = "INR"

    valuation_method: str = "NAV"

    assets: list[NAVAsset] = field(default_factory=list)

    liabilities: list[NAVLiability] = field(default_factory=list)

    minority_interest: float = 0.0

    holding_company_discount_pct: float = 0.0

    shares_outstanding: float = 1.0
