from __future__ import annotations

"""
==========================================================
DCF SENSITIVITY ANALYSIS ENGINE
Module  : sensitivity
Version : V1.0
==========================================================

Generates valuation sensitivity tables.

Current Support
---------------
• WACC × Terminal Growth

Future Extensions
-----------------
• Revenue Growth
• EBIT Margin
• CapEx
• Monte Carlo Simulation
"""

from dataclasses import dataclass

import numpy as np

# ==========================================================
# Result
# ==========================================================


@dataclass(slots=True)
class SensitivityResult:

    wacc_axis: list[float]

    terminal_growth_axis: list[float]

    implied_share_price_matrix: list[list[float]]

    def summary(self) -> dict:
        return {
            "rows": len(self.wacc_axis),
            "columns": len(self.terminal_growth_axis),
        }


# ==========================================================
# Helper
# ==========================================================


def _equity_value_to_share_price(
    enterprise_value: float,
    debt: float,
    cash: float,
    shares: float,
) -> float:

    equity = enterprise_value - debt + cash

    return equity / shares


# ==========================================================
# Main Engine
# ==========================================================


def build_sensitivity_matrix(
    final_year_fcff: float,
    pv_fcff_total: float,
    base_wacc: float,
    base_terminal_growth: float,
    forecast_years: int,
    debt: float,
    cash: float,
    shares: float,
    wacc_delta: float = 0.01,
    growth_delta: float = 0.005,
) -> SensitivityResult:

    wacc_axis = np.linspace(
        base_wacc - wacc_delta,
        base_wacc + wacc_delta,
        5,
    )

    growth_axis = np.linspace(
        base_terminal_growth - growth_delta,
        base_terminal_growth + growth_delta,
        5,
    )

    matrix = []

    for wacc in wacc_axis:

        row = []

        for growth in growth_axis:

            if growth >= wacc:

                row.append(float("nan"))

                continue

            terminal_fcff = final_year_fcff * (1 + growth)

            terminal_value = terminal_fcff / (wacc - growth)

            pv_terminal = terminal_value / ((1 + wacc) ** forecast_years)

            enterprise_value = pv_fcff_total + pv_terminal

            price = _equity_value_to_share_price(
                enterprise_value,
                debt,
                cash,
                shares,
            )

            row.append(price)

        matrix.append(row)

    return SensitivityResult(
        wacc_axis=wacc_axis.tolist(),
        terminal_growth_axis=growth_axis.tolist(),
        implied_share_price_matrix=matrix,
    )
