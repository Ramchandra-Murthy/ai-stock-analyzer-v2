from __future__ import annotations

"""
==========================================================
COMPARABLE COMPANY VALUATION MODEL
Module  : comparable_model
Version : V1.0
==========================================================

Institutional Comparable Company Analysis (CCA) model.

Pipeline
--------
Validate
    ↓
Peer Selection
    ↓
Calculate Multiples
    ↓
Statistical Analysis
    ↓
Apply Median Multiples & Sector Weighting
    ↓
Return ComparableResult
"""

from services.valuation.comparable.comparable_input import ComparableInput
from services.valuation.comparable.comparable_result import ComparableResult
from services.valuation.comparable.multiple_calculator import (
    calculate_multiples,
)
from services.valuation.comparable.peer_selection import select_peers
from services.valuation.comparable.statistics import (
    compute_statistics,
)
from services.valuation.comparable.validation import validate_input
from services.valuation.comparable.weighting import (
    DEFAULT_WEIGHTS,
)


class ComparableModel:

    def __init__(self, data: ComparableInput):
        self.data = data

    def run_model(self) -> ComparableResult:

        # -------------------------------------------------
        # Validation
        # -------------------------------------------------

        validate_input(self.data)

        # -------------------------------------------------
        # Peer Selection
        # -------------------------------------------------

        peers = select_peers(self.data.peers)

        if not peers:
            raise ValueError("No valid comparable companies available.")

        # -------------------------------------------------
        # Calculate Multiples
        # -------------------------------------------------

        peer_multiples = [calculate_multiples(peer) for peer in peers]

        ev_sales_values = [m.ev_sales for m in peer_multiples]
        ev_ebit_values = [m.ev_ebit for m in peer_multiples]
        ev_ebitda_values = [m.ev_ebitda for m in peer_multiples]
        pe_values = [m.pe for m in peer_multiples]
        pb_values = [m.pb for m in peer_multiples]

        # -------------------------------------------------
        # Statistics
        # -------------------------------------------------

        ev_sales_stats = compute_statistics(ev_sales_values)
        ev_ebit_stats = compute_statistics(ev_ebit_values)
        ev_ebitda_stats = compute_statistics(ev_ebitda_values)
        pe_stats = compute_statistics(pe_values)
        pb_stats = compute_statistics(pb_values)

        target = self.data.target

        # -------------------------------------------------
        # Apply Median Multiples
        # -------------------------------------------------

        implied_ev_sales = ev_sales_stats.median * target.revenue

        implied_ev_ebit = ev_ebit_stats.median * target.ebit

        implied_ev_ebitda = ev_ebitda_stats.median * target.ebitda

        implied_equity_pe = pe_stats.median * target.net_income

        implied_equity_pb = pb_stats.median * target.book_value

        # -------------------------------------------------
        # Recommended Values via Policy Weighting
        # -------------------------------------------------

        DEFAULT_WEIGHTS.validate()

        recommended_ev = (
            implied_ev_sales * DEFAULT_WEIGHTS.ev_sales
            + implied_ev_ebit * DEFAULT_WEIGHTS.ev_ebit
            + implied_ev_ebitda * DEFAULT_WEIGHTS.ev_ebitda
        )

        recommended_equity = recommended_ev - target.net_debt

        implied_share_price = recommended_equity / target.shares_outstanding

        # -------------------------------------------------
        # Result
        # -------------------------------------------------

        return ComparableResult(
            company_name=target.company_name,
            currency=self.data.currency,
            peer_count=len(peers),
            implied_enterprise_value_ev_sales=implied_ev_sales,
            implied_enterprise_value_ev_ebit=implied_ev_ebit,
            implied_enterprise_value_ev_ebitda=implied_ev_ebitda,
            implied_equity_value_pe=implied_equity_pe,
            implied_equity_value_pb=implied_equity_pb,
            recommended_enterprise_value=recommended_ev,
            recommended_equity_value=recommended_equity,
            implied_share_price=implied_share_price,
            median_ev_sales=ev_sales_stats.median,
            median_ev_ebit=ev_ebit_stats.median,
            median_ev_ebitda=ev_ebitda_stats.median,
            median_pe=pe_stats.median,
            median_pb=pb_stats.median,
            statistics={
                "ev_sales": ev_sales_stats,
                "ev_ebit": ev_ebit_stats,
                "ev_ebitda": ev_ebitda_stats,
                "pe": pe_stats,
                "pb": pb_stats,
            },
            validation_passed=True,
            warnings=[],
            diagnostics={
                "peer_multiples": peer_multiples,
            },
        )
