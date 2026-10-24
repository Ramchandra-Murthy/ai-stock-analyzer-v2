# ==========================================================
# SOTP V5 NET DEBT SERVICE
# ==========================================================

from services.sotp_balance_sheet_detail_service import (
    get_sotp_balance_sheet_details,
)


def _safe_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _round_value(value, digits=2):
    if value is None:
        return None
    return round(value, digits)


def generate_sotp_net_debt_bridge(symbol):
    """
    Build a transparent net-debt reconciliation for SOTP V5.

    Important:
    - Cash & equivalents are treated separately from investments.
    - Short-term investments are NOT automatically treated as cash.
    - Lease obligations are NOT separately deducted without determining
      whether they are already included in reported total debt.
    - Provider net debt is retained as a reference value.
    """

    details = get_sotp_balance_sheet_details(symbol)

    if not isinstance(details, dict):
        return {
            "status": "UNAVAILABLE",
            "symbol": symbol,
            "message": "Invalid balance-sheet detail result.",
        }

    if details.get("status") != "OK":
        return {
            "status": "UNAVAILABLE",
            "symbol": symbol,
            "message": details.get(
                "message",
                "Balance-sheet details unavailable.",
            ),
        }

    debt = details.get("debt", {})
    cash = details.get("cash", {})

    if not isinstance(debt, dict):
        debt = {}

    if not isinstance(cash, dict):
        cash = {}

    total_debt = _safe_float(debt.get("total_debt"))

    provider_net_debt = _safe_float(debt.get("provider_net_debt"))

    lease_obligations = _safe_float(debt.get("capital_lease_obligations"))

    cash_and_equivalents = _safe_float(cash.get("cash_and_equivalents"))

    restricted_cash = _safe_float(cash.get("restricted_cash"))

    short_term_investments = _safe_float(cash.get("short_term_investments"))

    cash_and_short_term = _safe_float(cash.get("cash_and_short_term_investments"))

    # ======================================================
    # BASE NET DEBT
    # ======================================================

    conservative_net_debt = None

    if total_debt is not None and cash_and_equivalents is not None:
        conservative_net_debt = total_debt - cash_and_equivalents

    # ======================================================
    # PROVIDER RECONCILIATION
    # ======================================================

    provider_gap = None

    if conservative_net_debt is not None and provider_net_debt is not None:
        provider_gap = conservative_net_debt - provider_net_debt

    lease_gap = None
    lease_gap_matches = False

    if provider_gap is not None and lease_obligations is not None:
        lease_gap = provider_gap - lease_obligations

        lease_gap_matches = abs(lease_gap) <= 1.0

    # ======================================================
    # CASH AGGREGATE RECONCILIATION
    # ======================================================

    calculated_cash_and_short_term = None
    cash_short_term_gap = None
    cash_short_term_reconciles = False

    if cash_and_equivalents is not None and short_term_investments is not None:
        calculated_cash_and_short_term = cash_and_equivalents + short_term_investments

    if calculated_cash_and_short_term is not None and cash_and_short_term is not None:
        cash_short_term_gap = cash_and_short_term - calculated_cash_and_short_term

        cash_short_term_reconciles = abs(cash_short_term_gap) <= 1.0

    # ======================================================
    # PROVISIONAL SOTP TREATMENT
    # ======================================================

    # Until the provider's exact net-debt methodology is established,
    # use the transparent debt-minus-cash figure as the conservative
    # SOTP bridge.
    provisional_sotp_net_debt = conservative_net_debt

    return {
        "status": "OK",
        "symbol": details.get("symbol", symbol),
        "period": details.get("period"),
        "currency": details.get("currency", "INR"),
        "unit": details.get("unit", "crore"),
        "debt": {
            "total_debt": _round_value(total_debt),
            "lease_obligations": _round_value(lease_obligations),
            "provider_net_debt": _round_value(provider_net_debt),
        },
        "cash": {
            "cash_and_equivalents": _round_value(cash_and_equivalents),
            "restricted_cash": _round_value(restricted_cash),
            "short_term_investments": _round_value(short_term_investments),
            "cash_and_short_term_investments": _round_value(cash_and_short_term),
        },
        "reconciliation": {
            "conservative_net_debt": _round_value(conservative_net_debt),
            "provider_net_debt": _round_value(provider_net_debt),
            "conservative_minus_provider": _round_value(provider_gap),
            "lease_obligations": _round_value(lease_obligations),
            "gap_minus_lease_obligations": _round_value(lease_gap),
            "gap_matches_lease_obligations": (lease_gap_matches),
            "cash_plus_short_term": _round_value(calculated_cash_and_short_term),
            "reported_cash_and_short_term": _round_value(cash_and_short_term),
            "cash_short_term_gap": _round_value(cash_short_term_gap),
            "cash_short_term_reconciles": (cash_short_term_reconciles),
        },
        "sotp_treatment": {
            "total_debt": "DEDUCT",
            "cash_and_equivalents": "ADD",
            "restricted_cash": "EXCLUDE_PENDING_REVIEW",
            "short_term_investments": "REVIEW",
            "lease_obligations": "DO_NOT_DEDUCT_SEPARATELY",
            "provider_net_debt": "REFERENCE",
        },
        "provisional_sotp_net_debt": _round_value(provisional_sotp_net_debt),
        "provisional_equity_bridge_adjustment": (
            _round_value(-provisional_sotp_net_debt)
            if provisional_sotp_net_debt is not None
            else None
        ),
        "status_view": "PROVISIONAL",
        "warnings": [
            (
                "The SOTP net-debt bridge currently uses total debt "
                "less cash and cash equivalents."
            ),
            (
                "Short-term investments are not treated as excess "
                "cash until their relationship with financial assets "
                "and operating requirements is resolved."
            ),
            (
                "Lease obligations are not separately deducted "
                "because doing so could double-count obligations "
                "already contained in total debt."
            ),
            (
                "Provider net debt is retained as a reconciliation "
                "reference rather than automatically used in the "
                "SOTP equity bridge."
            ),
        ],
    }
