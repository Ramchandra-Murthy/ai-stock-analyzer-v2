from __future__ import annotations

"""
==========================================================
COMPARABLE COMPANY INPUT MODEL
Module  : comparable_input
Version : V1.0
==========================================================

Defines immutable input contracts for Comparable Company
Analysis (CCA).

Used by:
    • ComparableModel
    • ComparableEngine
    • Valuation Dispatcher
"""

from dataclasses import dataclass, field

# ==========================================================
# Peer Company
# ==========================================================


@dataclass(slots=True)
class PeerCompany:
    """
    Represents a comparable peer company.
    """

    name: str
    ticker: str
    enterprise_value: float
    market_cap: float
    revenue: float
    ebit: float
    ebitda: float
    net_income: float
    book_value: float
    shares_outstanding: float
    share_price: float


# ==========================================================
# Target Company
# ==========================================================


@dataclass(slots=True)
class TargetCompany:
    """
    Financial metrics for the company being valued.
    """

    company_name: str
    revenue: float
    ebit: float
    ebitda: float
    net_income: float
    book_value: float
    net_debt: float
    shares_outstanding: float


# ==========================================================
# Comparable Input
# ==========================================================


@dataclass(slots=True)
class ComparableInput:
    """
    Master input consumed by the Comparable valuation model.
    """

    target: TargetCompany
    peers: list[PeerCompany] = field(default_factory=list)
    currency: str = "INR"
