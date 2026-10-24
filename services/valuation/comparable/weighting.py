from __future__ import annotations

"""
==========================================================
COMPARABLE VALUATION WEIGHTING
Module  : weighting
Version : V1.0
==========================================================

Defines weighting schemes for combining valuation
multiples into a recommended enterprise value.

Industry-specific schemes can be added without changing
ComparableModel.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ComparableWeights:
    ev_sales: float
    ev_ebit: float
    ev_ebitda: float

    def validate(self) -> None:
        total = self.ev_sales + self.ev_ebit + self.ev_ebitda

        if abs(total - 1.0) > 1e-6:
            raise ValueError("Comparable weights must sum to 1.0.")


# ==========================================================
# Default Institutional Scheme
# ==========================================================

DEFAULT_WEIGHTS = ComparableWeights(
    ev_sales=0.20,
    ev_ebit=0.40,
    ev_ebitda=0.40,
)

# ==========================================================
# Sector Templates
# ==========================================================

SAAS_WEIGHTS = ComparableWeights(
    ev_sales=0.70,
    ev_ebit=0.10,
    ev_ebitda=0.20,
)

MANUFACTURING_WEIGHTS = ComparableWeights(
    ev_sales=0.10,
    ev_ebit=0.40,
    ev_ebitda=0.50,
)

RETAIL_WEIGHTS = ComparableWeights(
    ev_sales=0.30,
    ev_ebit=0.30,
    ev_ebitda=0.40,
)

BANKING_WEIGHTS = ComparableWeights(
    ev_sales=0.00,
    ev_ebit=0.00,
    ev_ebitda=0.00,
)
