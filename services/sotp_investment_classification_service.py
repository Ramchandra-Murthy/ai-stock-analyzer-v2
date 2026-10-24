# ==========================================================
# SOTP V5 INVESTMENT CLASSIFICATION SERVICE
# ==========================================================

from services.sotp_balance_sheet_detail_service import (
    get_sotp_balance_sheet_details,
)
from services.sotp_investment_service import (
    analyze_financial_asset_composition,
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


def classify_sotp_investment_assets(symbol):
    """
    Classify investment-related balance-sheet assets for SOTP V5.

    This service intentionally does NOT add investment assets to the
    equity bridge. It establishes their accounting hierarchy and
    provisional valuation treatment first.
    """

    details = get_sotp_balance_sheet_details(symbol)

    composition = analyze_financial_asset_composition(symbol)

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

    cash = details.get("cash", {})
    investments = details.get("investments", {})

    if not isinstance(cash, dict):
        cash = {}

    if not isinstance(investments, dict):
        investments = {}

    short_term = _safe_float(cash.get("short_term_investments"))

    financial_assets = _safe_float(investments.get("financial_investments"))

    long_term_equity = _safe_float(investments.get("long_term_equity_investment"))

    joint_ventures = _safe_float(investments.get("joint_venture_investments"))

    associates = _safe_float(investments.get("associate_investments"))

    # ======================================================
    # FINANCIAL-ASSET COMPOSITION
    # ======================================================

    financial_asset_detail = {}

    if isinstance(composition, dict):
        financial_asset_detail = composition.get(
            "financial_assets",
            {},
        )

    if not isinstance(financial_asset_detail, dict):
        financial_asset_detail = {}

    afs = _safe_float(financial_asset_detail.get("available_for_sale_securities"))

    fvtpl = _safe_float(financial_asset_detail.get("fvtpl_financial_assets"))

    # ======================================================
    # RECONCILIATIONS
    # ======================================================

    afs_plus_fvtpl = None
    financial_asset_gap = None
    financial_assets_reconcile = False

    if afs is not None and fvtpl is not None:
        afs_plus_fvtpl = afs + fvtpl

    if afs_plus_fvtpl is not None and financial_assets is not None:
        financial_asset_gap = financial_assets - afs_plus_fvtpl

        financial_assets_reconcile = abs(financial_asset_gap) <= 1.0

    jv_plus_associates = None
    long_term_equity_gap = None
    long_term_equity_reconciles = False

    if joint_ventures is not None and associates is not None:
        jv_plus_associates = joint_ventures + associates

    if jv_plus_associates is not None and long_term_equity is not None:
        long_term_equity_gap = long_term_equity - jv_plus_associates

        long_term_equity_reconciles = abs(long_term_equity_gap) <= 1.0

    # ======================================================
    # PROVISIONAL CLASSIFICATION
    # ======================================================

    assets = {
        "short_term_investments": {
            "value": _round_value(short_term),
            "balance_sheet_class": "CURRENT",
            "classification": "INVESTMENT_ASSET",
            "sotp_treatment": "REVIEW",
            "reason": (
                "Current investment balance is distinct from cash "
                "and equivalents but requires confirmation of "
                "operating liquidity requirements and overlap."
            ),
        },
        "financial_investments": {
            "value": _round_value(financial_assets),
            "balance_sheet_class": "NON_CURRENT",
            "classification": "FINANCIAL_ASSET_AGGREGATE",
            "sotp_treatment": "REVIEW",
            "reason": (
                "Non-current financial assets reconcile to AFS and "
                "FVTPL components but require review for overlap "
                "with operating or separately valued assets."
            ),
        },
        "available_for_sale_securities": {
            "value": _round_value(afs),
            "balance_sheet_class": "NON_CURRENT",
            "classification": ("COMPONENT_OF_FINANCIAL_ASSETS"),
            "sotp_treatment": "DO_NOT_ADD_SEPARATELY",
        },
        "fvtpl_financial_assets": {
            "value": _round_value(fvtpl),
            "balance_sheet_class": "NON_CURRENT",
            "classification": ("COMPONENT_OF_FINANCIAL_ASSETS"),
            "sotp_treatment": "DO_NOT_ADD_SEPARATELY",
        },
        "long_term_equity_investment": {
            "value": _round_value(long_term_equity),
            "balance_sheet_class": "NON_CURRENT",
            "classification": "EQUITY_INVESTMENT_AGGREGATE",
            "sotp_treatment": "REVIEW",
            "reason": (
                "Aggregate reconciles to JV and associate "
                "investments. Ownership and operating overlap must "
                "be reviewed before inclusion in SOTP."
            ),
        },
        "joint_venture_investments": {
            "value": _round_value(joint_ventures),
            "balance_sheet_class": "NON_CURRENT",
            "classification": ("COMPONENT_OF_LONG_TERM_EQUITY"),
            "sotp_treatment": "DO_NOT_ADD_SEPARATELY",
        },
        "associate_investments": {
            "value": _round_value(associates),
            "balance_sheet_class": "NON_CURRENT",
            "classification": ("COMPONENT_OF_LONG_TERM_EQUITY"),
            "sotp_treatment": "DO_NOT_ADD_SEPARATELY",
        },
    }

    # ======================================================
    # TOTALS — DIAGNOSTIC ONLY
    # ======================================================

    review_asset_total = 0.0
    review_asset_count = 0

    for item in assets.values():

        if item.get("sotp_treatment") != "REVIEW":
            continue

        value = item.get("value")

        if isinstance(value, (int, float)):
            review_asset_total += value
            review_asset_count += 1

    return {
        "status": "OK",
        "symbol": details.get("symbol", symbol),
        "period": details.get("period"),
        "currency": details.get("currency", "INR"),
        "unit": details.get("unit", "crore"),
        "assets": assets,
        "reconciliation": {
            "afs_plus_fvtpl": _round_value(afs_plus_fvtpl),
            "financial_assets": _round_value(financial_assets),
            "financial_asset_gap": _round_value(financial_asset_gap),
            "financial_assets_reconcile": (financial_assets_reconcile),
            "jv_plus_associates": _round_value(jv_plus_associates),
            "long_term_equity": _round_value(long_term_equity),
            "long_term_equity_gap": _round_value(long_term_equity_gap),
            "long_term_equity_reconciles": (long_term_equity_reconciles),
        },
        "review_asset_count": review_asset_count,
        "review_asset_total": _round_value(review_asset_total),
        "review_asset_total_is_additive": False,
        "status_view": "REVIEW_REQUIRED",
        "warnings": [
            (
                "The review asset total is diagnostic only and must "
                "not be added directly to SOTP equity value."
            ),
            (
                "Available-for-sale and FVTPL balances are "
                "components of Investment in Financial Assets and "
                "must not be counted separately."
            ),
            (
                "JV and associate balances are components of "
                "Long-Term Equity Investment and must not be "
                "counted separately."
            ),
            (
                "Current short-term investments and non-current "
                "financial assets appear in different balance-sheet "
                "sections, but economic overlap or operating "
                "requirements must still be reviewed."
            ),
        ],
    }
