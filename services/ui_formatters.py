"""Reusable formatting helpers for the Streamlit UI.

The helpers are dependency-light so unit tests can exercise evidence-display
contracts without importing the full Streamlit application.
"""

from __future__ import annotations

import math


def _finite_number(value):
    """Return a finite float, or None for missing/invalid/non-finite input."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def format_market_cap(value):
    """Format market capitalization without displaying invalid evidence as valid."""
    number = _finite_number(value)
    if number is None or number < 0:
        return "N/A"

    if number >= 1e12:
        return f"₹{number / 1e12:.2f} Lakh Cr"
    if number >= 1e9:
        return f"₹{number / 1e7:.2f} Cr"
    if number >= 1e6:
        return f"₹{number / 1e5:.2f} Lakh"
    return f"₹{number:,.0f}"


def format_percent(value):
    """Convert finite decimal values to percentages."""
    if value in [None, "N/A"]:
        return "N/A"

    number = _finite_number(value)
    if number is None or abs(number) > 10:
        return "N/A"

    return f"{number * 100:.2f}%"


def format_dividend_yield(value):
    """Format Yahoo Finance dividendYield values already expressed as percent."""
    if value in [None, "N/A"]:
        return "N/A"

    number = _finite_number(value)
    if number is None:
        return "N/A"

    return f"{number:.2f}%"


def safe_progress(value):
    """Convert a finite 0-100 score into a Streamlit progress value."""
    score = _finite_number(value)
    if score is None or score < 0 or score > 100:
        return 0.0
    return score / 100.0


def format_price(value):
    """Safely format a finite positive price."""
    number = _finite_number(value)
    if number is None or number <= 0:
        return "N/A"
    return f"₹{number:,.2f}"


def format_ratio(value):
    """Format a finite positive financial ratio."""
    number = _finite_number(value)
    if number is None or number <= 0:
        return "N/A"
    return f"{number:.2f}x"


def format_debt_to_equity(value):
    """Format Yahoo Finance debtToEquity values reported on a percentage scale."""
    number = _finite_number(value)
    if number is None or number < 0 or number > 10000:
        return "N/A"
    return f"{number / 100.0:.2f}x"


def format_large_rupees(value):
    """Format large rupee-denominated financial values."""
    number = _finite_number(value)
    if number is None:
        return "N/A"

    if number >= 1e12:
        return f"Rs. {number / 1e12:.2f} Lakh Cr"
    if number >= 1e7:
        return f"Rs. {number / 1e7:,.2f} Cr"
    if number >= 1e5:
        return f"Rs. {number / 1e5:,.2f} Lakh"
    return f"Rs. {number:,.2f}"
