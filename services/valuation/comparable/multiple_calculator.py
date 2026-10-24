from __future__ import annotations

"""
==========================================================
COMPARABLE MULTIPLE CALCULATOR
Module  : multiple_calculator
Version : V1.0
==========================================================

Calculates valuation multiples for peer companies.

Enterprise Multiples
--------------------
• EV / Revenue
• EV / EBIT
• EV / EBITDA

Equity Multiples
----------------
• P/E
• P/B
"""

from dataclasses import dataclass

from services.valuation.comparable.comparable_input import (
    PeerCompany,
)

# ==========================================================
# Multiple Container
# ==========================================================


@dataclass(slots=True)
class ComparableMultiples:

    ev_sales: float

    ev_ebit: float

    ev_ebitda: float

    pe: float

    pb: float


# ==========================================================
# Enterprise Multiples
# ==========================================================


def ev_sales(peer: PeerCompany) -> float:

    return peer.enterprise_value / peer.revenue


def ev_ebit(peer: PeerCompany) -> float:

    return peer.enterprise_value / peer.ebit


def ev_ebitda(peer: PeerCompany) -> float:

    return peer.enterprise_value / peer.ebitda


# ==========================================================
# Equity Multiples
# ==========================================================


def pe(peer: PeerCompany) -> float:

    return peer.market_cap / peer.net_income


def pb(peer: PeerCompany) -> float:

    return peer.market_cap / peer.book_value


# ==========================================================
# Aggregate Calculator
# ==========================================================


def calculate_multiples(
    peer: PeerCompany,
) -> ComparableMultiples:

    return ComparableMultiples(
        ev_sales=ev_sales(peer),
        ev_ebit=ev_ebit(peer),
        ev_ebitda=ev_ebitda(peer),
        pe=pe(peer),
        pb=pb(peer),
    )
