import math

from services.research_service import (
    get_stock_profile,
)

# ==========================================================
# HELPERS
# ==========================================================


def _safe_float(value):
    """Convert value to finite float or return None."""

    try:
        value = float(value)

        if math.isnan(value) or math.isinf(value):
            return None

        return value

    except (TypeError, ValueError):
        return None


def _clean_symbol(symbol):
    """Normalize NSE symbol."""

    if not symbol:
        return ""

    symbol = str(symbol).strip().upper()

    if symbol.endswith(".NS"):
        symbol = symbol[:-3]

    return symbol


def _inr_to_crore(value):
    """Convert raw INR into INR crore."""

    value = _safe_float(value)

    if value is None:
        return None

    return value / 10_000_000.0


# ==========================================================
# SOTP BALANCE SHEET DATA
# ==========================================================


def get_sotp_balance_sheet_data(symbol):
    """
    Extract and normalize balance-sheet fields required
    by the SOTP V5 equity bridge.

    research_service values are raw INR.
    SOTP V5 operates in INR crore.

    IMPORTANT:
    total_cash is retained under its upstream definition.
    It must not automatically be combined with separately
    identified investments without checking for overlap.
    """

    base_symbol = _clean_symbol(symbol)

    try:
        profile = get_stock_profile(base_symbol)

    except Exception as error:
        return {
            "status": "UNAVAILABLE",
            "symbol": base_symbol,
            "message": str(error),
        }

    if not isinstance(profile, dict):
        return {
            "status": "UNAVAILABLE",
            "symbol": base_symbol,
            "message": "Invalid stock profile.",
        }

    gross_debt_raw = _safe_float(profile.get("total_debt"))

    total_cash_raw = _safe_float(profile.get("total_cash"))

    enterprise_value_raw = _safe_float(profile.get("enterprise_value"))

    market_cap_raw = _safe_float(profile.get("market_cap"))

    shares_outstanding = _safe_float(profile.get("shares_outstanding"))

    gross_debt = _inr_to_crore(gross_debt_raw)

    total_cash = _inr_to_crore(total_cash_raw)

    enterprise_value = _inr_to_crore(enterprise_value_raw)

    market_cap = _inr_to_crore(market_cap_raw)

    # ------------------------------------------------------
    # SIMPLE NET DEBT
    # ------------------------------------------------------

    simple_net_debt = None

    if gross_debt is not None and total_cash is not None:
        simple_net_debt = gross_debt - total_cash

        # ------------------------------------------------------
    # ENTERPRISE VALUE RECONCILIATION
    # ------------------------------------------------------

    implied_ev = None
    ev_reconciliation_gap = None
    implied_total_ev_adjustment = None

    if market_cap is not None and simple_net_debt is not None:
        implied_ev = market_cap + simple_net_debt

    if enterprise_value is not None and implied_ev is not None:
        ev_reconciliation_gap = enterprise_value - implied_ev

        # This represents the aggregate amount required
        # to reconcile:
        #
        # Market Cap + Debt - Cash
        #
        # with the upstream provider's reported EV.
        #
        # It is diagnostic only. It must NOT automatically
        # be treated as debt, minority interest, leases,
        # preferred equity or another specific adjustment.
        implied_total_ev_adjustment = ev_reconciliation_gap

    # ------------------------------------------------------
    # AVAILABILITY
    # ------------------------------------------------------

    available_fields = 0

    required_values = [
        gross_debt,
        total_cash,
        shares_outstanding,
    ]

    for value in required_values:
        if value is not None:
            available_fields += 1

    coverage = available_fields / len(required_values)

    return {
        "status": "OK",
        "symbol": base_symbol,
        "currency": profile.get(
            "currency",
            "INR",
        ),
        "unit": "crore",
        "gross_debt": (round(gross_debt, 2) if gross_debt is not None else None),
        "total_cash": (round(total_cash, 2) if total_cash is not None else None),
        "simple_net_debt": (round(simple_net_debt, 2) if simple_net_debt is not None else None),
        "market_cap": (round(market_cap, 2) if market_cap is not None else None),
        "reported_enterprise_value": (
            round(enterprise_value, 2) if enterprise_value is not None else None
        ),
        "implied_ev_from_simple_net_debt": (
            round(implied_ev, 2) if implied_ev is not None else None
        ),
        "ev_reconciliation_gap": (
            round(ev_reconciliation_gap, 2) if ev_reconciliation_gap is not None else None
        ),
        "implied_total_ev_adjustment": (
            round(implied_total_ev_adjustment, 2)
            if implied_total_ev_adjustment is not None
            else None
        ),
        "shares_outstanding": shares_outstanding,
        "coverage": round(
            coverage,
            4,
        ),
        "coverage_percent": round(
            coverage * 100.0,
            1,
        ),
        "source": ("Normalized stock profile data from " "research_service"),
        "warnings": [
            (
                "total_cash follows the upstream data "
                "provider definition and may include "
                "cash-like or short-term investment items."
            ),
            (
                "simple_net_debt is provisional and should "
                "not be used for final SOTP equity valuation "
                "until overlap with investments and other "
                "balance-sheet adjustments is reviewed."
            ),
            (
                "The EV reconciliation gap is diagnostic only. "
                "It must not be automatically classified as debt, "
                "minority interest, lease liabilities or another "
                "specific SOTP adjustment."
            ),
        ],
    }
