from __future__ import annotations

"""
==========================================================
DCF TERMINAL VALUE ENGINE
Module  : terminal_value
Version : V1.0
==========================================================

Computes the terminal value using the Gordon Growth Model
and discounts it back to present value.

Contains:
    • Terminal FCFF
    • Terminal Value
    • Present Value of Terminal Value
    • Terminal Value Contribution

Contains NO:
    • Forecast Logic
    • Explicit FCFF Discounting
"""

from dataclasses import dataclass

# ==========================================================
# Terminal Value Result
# ==========================================================


@dataclass(slots=True)
class TerminalValueResult:
    """
    Terminal value calculation results.
    """

    terminal_fcff: float

    terminal_value: float

    present_value_terminal: float

    terminal_value_pct_of_ev: float = 0.0

    def summary(self) -> dict:
        return {
            "terminal_fcff": self.terminal_fcff,
            "terminal_value": self.terminal_value,
            "present_value_terminal": self.present_value_terminal,
            "terminal_value_pct_of_ev": self.terminal_value_pct_of_ev,
        }


# ==========================================================
# Terminal FCFF
# ==========================================================


def compute_terminal_fcff(
    final_year_fcff: float,
    terminal_growth_rate: float,
) -> float:
    """
    FCFF_(n+1)
    """

    return final_year_fcff * (1.0 + terminal_growth_rate)


# ==========================================================
# Gordon Growth Terminal Value
# ==========================================================


def compute_terminal_value(
    terminal_fcff: float,
    wacc: float,
    terminal_growth_rate: float,
) -> float:
    """
    TV = FCFF_(n+1) / (WACC - g)
    """

    if terminal_growth_rate >= wacc:
        raise ValueError("Terminal growth rate must be less than WACC.")

    return terminal_fcff / (wacc - terminal_growth_rate)


# ==========================================================
# Present Value of Terminal Value
# ==========================================================


def discount_terminal_value(
    terminal_value: float,
    wacc: float,
    forecast_years: int,
) -> float:
    """
    Discount terminal value to present value.
    """

    return terminal_value / ((1.0 + wacc) ** forecast_years)


# ==========================================================
# Contribution
# ==========================================================


def terminal_value_contribution(
    pv_terminal: float,
    enterprise_value: float,
) -> float:
    """
    Returns percentage contribution of terminal value to EV.
    """

    if enterprise_value == 0:
        return 0.0

    return (pv_terminal / enterprise_value) * 100.0


# ==========================================================
# Master Routine
# ==========================================================


def build_terminal_value(
    final_year_fcff: float,
    wacc: float,
    terminal_growth_rate: float,
    forecast_years: int,
    pv_fcff_total: float,
) -> TerminalValueResult:
    """
    Complete terminal value routine.
    """

    terminal_fcff = compute_terminal_fcff(
        final_year_fcff,
        terminal_growth_rate,
    )

    terminal_value = compute_terminal_value(
        terminal_fcff,
        wacc,
        terminal_growth_rate,
    )

    pv_terminal = discount_terminal_value(
        terminal_value,
        wacc,
        forecast_years,
    )

    enterprise_value = pv_fcff_total + pv_terminal

    contribution = terminal_value_contribution(
        pv_terminal,
        enterprise_value,
    )

    return TerminalValueResult(
        terminal_fcff=terminal_fcff,
        terminal_value=terminal_value,
        present_value_terminal=pv_terminal,
        terminal_value_pct_of_ev=contribution,
    )
