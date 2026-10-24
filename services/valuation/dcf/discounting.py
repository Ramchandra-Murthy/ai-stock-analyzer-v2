from __future__ import annotations

"""
==========================================================
DCF DISCOUNTING ENGINE
Module  : discounting
Version : V1.0
==========================================================

Responsible ONLY for discounting projected Free Cash Flow
to Firm (FCFF) into present value.

Contains:
    • Discount Factor Calculation
    • Present Value of FCFF
    • Explicit Forecast PV Aggregation

Contains NO:
    • Forecast Logic
    • Terminal Value Logic
    • Enterprise Value Logic
"""

from dataclasses import dataclass

# ==========================================================
# Discount Schedule
# ==========================================================


@dataclass(slots=True)
class DiscountSchedule:
    """
    Holds all discounting outputs for the explicit
    forecast period.
    """

    discount_factors: list[float]

    present_value_fcff: list[float]

    pv_fcff_total: float

    @property
    def years(self) -> int:
        return len(self.discount_factors)

    def summary(self) -> dict:
        return {
            "forecast_years": self.years,
            "pv_fcff_total": self.pv_fcff_total,
        }


# ==========================================================
# Discount Factors
# ==========================================================


def compute_discount_factors(
    wacc: float,
    forecast_years: int,
) -> list[float]:
    """
    Computes discount factors:

        DF = (1 + WACC)^t
    """

    return [(1.0 + wacc) ** (year + 1) for year in range(forecast_years)]


# ==========================================================
# Present Value of FCFF
# ==========================================================


def discount_fcff(
    projected_fcff: list[float],
    discount_factors: list[float],
) -> list[float]:
    """
    Discounts each projected FCFF.
    """

    return [projected_fcff[i] / discount_factors[i] for i in range(len(projected_fcff))]


# ==========================================================
# Aggregate PV
# ==========================================================


def aggregate_present_value(
    pv_fcff: list[float],
) -> float:
    """
    Sum of discounted explicit FCFF.
    """

    return sum(pv_fcff)


# ==========================================================
# Master Routine
# ==========================================================


def build_discount_schedule(
    projected_fcff: list[float],
    wacc: float,
) -> DiscountSchedule:
    """
    Complete explicit-period discounting routine.
    """

    factors = compute_discount_factors(
        wacc,
        len(projected_fcff),
    )

    pv = discount_fcff(
        projected_fcff,
        factors,
    )

    total = aggregate_present_value(
        pv,
    )

    return DiscountSchedule(
        discount_factors=factors,
        present_value_fcff=pv,
        pv_fcff_total=total,
    )
