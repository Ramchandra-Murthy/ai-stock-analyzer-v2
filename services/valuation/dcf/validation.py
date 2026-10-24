from __future__ import annotations

"""
==========================================================
DCF INPUT VALIDATION
Module  : validation
Version : V2.0
==========================================================

Validates all assumptions before the DCF engine executes.
Raises ValueError whenever assumptions are inconsistent or mathematically invalid.
"""

from .dcf_input import DCFInput


def validate_input(data: DCFInput) -> None:
    """
    Main validation entry point.
    """
    _validate_history(data)
    _validate_forecast_lengths(data)
    _validate_rates(data)
    _validate_capital_structure(data)
    _validate_terminal_growth(data)
    _validate_balance_sheet(data)
    _validate_share_count(data)


# ==========================================================
# Historical Financials
# ==========================================================


def _validate_history(data: DCFInput) -> None:
    if data.last_historical_revenue is None or data.last_historical_revenue <= 0:
        raise ValueError("last_historical_revenue must be strictly greater than 0.")


# ==========================================================
# Forecast Arrays
# ==========================================================


def _validate_forecast_lengths(data: DCFInput) -> None:
    n = len(data.revenue_growth_rates)
    if n == 0:
        raise ValueError("Revenue growth rates forecast cannot be empty.")

    arrays = {
        "ebit_margin_forecast": data.ebit_margin_forecast,
        "dna_pct_rev": data.dna_pct_rev,
        "capex_pct_rev": data.capex_pct_rev,
        "nwc_pct_rev": data.nwc_pct_rev,
    }

    for name, arr in arrays.items():
        if len(arr) != n:
            raise ValueError(f"Array length mismatch for '{name}': expected {n}, got {len(arr)}.")


# ==========================================================
# Rates
# ==========================================================


def _validate_rates(data: DCFInput) -> None:
    if not (0 <= data.tax_rate <= 1):
        raise ValueError("Tax rate must be between 0 and 1.")

    if data.cost_of_equity <= 0:
        raise ValueError("Cost of equity must be positive.")

    if data.cost_of_debt_post_tax < 0:
        raise ValueError("Cost of debt cannot be negative.")

    if data.cost_of_equity > 1:
        raise ValueError("Cost of equity should be expressed as a decimal (e.g. 0.12).")

    if data.cost_of_debt_post_tax > 1:
        raise ValueError("Cost of debt should be expressed as a decimal.")


# ==========================================================
# Capital Structure
# ==========================================================


def _validate_capital_structure(data: DCFInput) -> None:
    total = data.equity_weight + data.debt_weight

    if abs(total - 1.0) > 1e-4:
        raise ValueError(f"Capital structure weights must sum to 1.0 (got {total:.4f}).")

    if data.equity_weight < 0:
        raise ValueError("Equity weight cannot be negative.")

    if data.debt_weight < 0:
        raise ValueError("Debt weight cannot be negative.")


# ==========================================================
# Terminal Growth
# ==========================================================


def _validate_terminal_growth(data: DCFInput) -> None:
    wacc = data.calculate_wacc()

    if data.terminal_growth_rate >= wacc:
        raise ValueError(
            f"Terminal growth rate ({data.terminal_growth_rate:.2%}) must be lower than WACC ({wacc:.2%})."
        )

    if data.terminal_growth_rate < -0.05:
        raise ValueError("Terminal growth assumption appears unrealistic.")


# ==========================================================
# Balance Sheet
# ==========================================================


def _validate_balance_sheet(data: DCFInput) -> None:
    if data.total_debt < 0:
        raise ValueError("Debt cannot be negative.")

    if data.cash_and_equivalents < 0:
        raise ValueError("Cash cannot be negative.")


# ==========================================================
# Shares Outstanding
# ==========================================================


def _validate_share_count(data: DCFInput) -> None:
    if data.shares_outstanding <= 0:
        raise ValueError("Shares outstanding must be greater than zero.")
