from __future__ import annotations

"""
==========================================================
NAV SENSITIVITY ANALYSIS ENGINE
Module  : sensitivity
Version : V1.0
==========================================================

Generates sensitivity analysis for NAV valuation.

Current Support
---------------
• Holding Company Discount
• Fair Value Adjustment Multiplier

Future Extensions
-----------------
• Minority Interest
• Asset-specific valuation scenarios
• Monte Carlo simulation
"""

from dataclasses import dataclass

import numpy as np

# ==========================================================
# Result
# ==========================================================


@dataclass(slots=True)
class NAVSensitivityResult:
    """
    Stores NAV sensitivity output.
    """

    holdco_discount_axis: list[float]
    fair_value_multiplier_axis: list[float]
    equity_value_matrix: list[list[float]]
    implied_share_price_matrix: list[list[float]]

    def summary(self) -> dict:
        return {
            "rows": len(self.holdco_discount_axis),
            "columns": len(self.fair_value_multiplier_axis),
        }


# ==========================================================
# Main Engine
# ==========================================================


def build_nav_sensitivity_matrix(
    gross_asset_value: float,
    total_liabilities: float,
    minority_interest: float,
    shares_outstanding: float,
    base_holdco_discount: float,
    holdco_delta: float = 0.10,
    fair_value_delta: float = 0.10,
) -> NAVSensitivityResult:
    """
    Generates a 5x5 NAV sensitivity matrix.
    """

    holdco_axis = np.linspace(
        max(0.0, base_holdco_discount - holdco_delta),
        min(0.50, base_holdco_discount + holdco_delta),
        5,
    )

    fair_value_axis = np.linspace(
        1.0 - fair_value_delta,
        1.0 + fair_value_delta,
        5,
    )

    equity_matrix = []
    price_matrix = []

    for discount in holdco_axis:

        equity_row = []
        price_row = []

        for multiplier in fair_value_axis:

            adjusted_assets = gross_asset_value * multiplier

            nav = adjusted_assets - total_liabilities

            adjusted_nav = nav - minority_interest

            equity_value = adjusted_nav * (1.0 - discount)

            share_price = equity_value / shares_outstanding if shares_outstanding > 0 else 0.0

            equity_row.append(equity_value)
            price_row.append(share_price)

        equity_matrix.append(equity_row)
        price_matrix.append(price_row)

    return NAVSensitivityResult(
        holdco_discount_axis=holdco_axis.tolist(),
        fair_value_multiplier_axis=fair_value_axis.tolist(),
        equity_value_matrix=equity_matrix,
        implied_share_price_matrix=price_matrix,
    )
