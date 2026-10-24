# ==========================================================
# SOTP V5 INVESTMENT POLICY SERVICE
# ==========================================================

from services.sotp_investment_classification_service import (
    classify_sotp_investment_assets,
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


def generate_sotp_investment_policy(symbol):
    """
    Convert classified investment assets into a conservative
    SOTP V5 investment-adjustment policy.

    The policy distinguishes:

    INCLUDED
        Safe to include in the current equity bridge.

    EXCLUDED
        Known component/duplicate; must not be added separately.

    PENDING
        Potential non-operating asset, but classification or
        economic overlap has not yet been sufficiently resolved.

    The service deliberately does not assume that every investment
    balance represents incremental equity value.
    """

    classification = classify_sotp_investment_assets(symbol)

    if not isinstance(classification, dict):
        return {
            "status": "UNAVAILABLE",
            "symbol": symbol,
            "message": "Invalid investment classification result.",
        }

    if classification.get("status") != "OK":
        return {
            "status": "UNAVAILABLE",
            "symbol": symbol,
            "message": classification.get(
                "message",
                "Investment classification unavailable.",
            ),
        }

    assets = classification.get("assets", {})

    if not isinstance(assets, dict):
        assets = {}

    # ======================================================
    # PRIMARY ASSET POOLS
    # ======================================================

    short_term = assets.get(
        "short_term_investments",
        {},
    )

    financial = assets.get(
        "financial_investments",
        {},
    )

    long_term = assets.get(
        "long_term_equity_investment",
        {},
    )

    if not isinstance(short_term, dict):
        short_term = {}

    if not isinstance(financial, dict):
        financial = {}

    if not isinstance(long_term, dict):
        long_term = {}

    short_term_value = _safe_float(short_term.get("value"))

    financial_value = _safe_float(financial.get("value"))

    long_term_value = _safe_float(long_term.get("value"))

    # ======================================================
    # POLICY
    # ======================================================

    policy = {
        "short_term_investments": {
            "reported_value": _round_value(short_term_value),
            "policy_status": "PENDING",
            "included_value": 0.0,
            "treatment": "DO_NOT_ADD_YET",
            "reason": (
                "The balance is a current investment asset and is "
                "separate from cash and equivalents, but its "
                "operating liquidity requirement and economic "
                "classification have not yet been established."
            ),
        },
        "financial_investments": {
            "reported_value": _round_value(financial_value),
            "policy_status": "PENDING",
            "included_value": 0.0,
            "treatment": "DO_NOT_ADD_YET",
            "reason": (
                "The non-current financial asset aggregate is "
                "accountingly reconciled, but its relationship to "
                "operating businesses and other SOTP assets must "
                "be established before inclusion."
            ),
        },
        "long_term_equity_investment": {
            "reported_value": _round_value(long_term_value),
            "policy_status": "PENDING",
            "included_value": 0.0,
            "treatment": "DO_NOT_ADD_YET",
            "reason": (
                "JV and associate carrying values reconcile to "
                "this aggregate. The aggregate may represent "
                "incremental equity value, but ownership and "
                "operating overlap require review."
            ),
        },
        # Components already captured by aggregates
        "available_for_sale_securities": {
            "policy_status": "EXCLUDED",
            "included_value": 0.0,
            "treatment": "COMPONENT_ONLY",
            "reason": ("Already included within Investment in " "Financial Assets."),
        },
        "fvtpl_financial_assets": {
            "policy_status": "EXCLUDED",
            "included_value": 0.0,
            "treatment": "COMPONENT_ONLY",
            "reason": ("Already included within Investment in " "Financial Assets."),
        },
        "joint_venture_investments": {
            "policy_status": "EXCLUDED",
            "included_value": 0.0,
            "treatment": "COMPONENT_ONLY",
            "reason": ("Already included within Long-Term Equity " "Investment."),
        },
        "associate_investments": {
            "policy_status": "EXCLUDED",
            "included_value": 0.0,
            "treatment": "COMPONENT_ONLY",
            "reason": ("Already included within Long-Term Equity " "Investment."),
        },
    }

    # ======================================================
    # INCLUDED ADJUSTMENT
    # ======================================================

    included_adjustment = 0.0

    for item in policy.values():

        if not isinstance(item, dict):
            continue

        included_value = _safe_float(item.get("included_value"))

        if included_value is not None:
            included_adjustment += included_value

    # ======================================================
    # PENDING EXPOSURE
    # ======================================================

    pending_values = [
        short_term_value,
        financial_value,
        long_term_value,
    ]

    pending_exposure = sum(value for value in pending_values if isinstance(value, (int, float)))

    pending_count = sum(
        1
        for item in policy.values()
        if isinstance(item, dict) and item.get("policy_status") == "PENDING"
    )

    excluded_count = sum(
        1
        for item in policy.values()
        if isinstance(item, dict) and item.get("policy_status") == "EXCLUDED"
    )

    return {
        "status": "OK",
        "symbol": classification.get(
            "symbol",
            symbol,
        ),
        "period": classification.get("period"),
        "currency": classification.get(
            "currency",
            "INR",
        ),
        "unit": classification.get(
            "unit",
            "crore",
        ),
        "policy": policy,
        "included_investment_adjustment": (_round_value(included_adjustment)),
        "pending_investment_exposure": (_round_value(pending_exposure)),
        "pending_asset_count": pending_count,
        "excluded_component_count": excluded_count,
        "bridge_ready": pending_count == 0,
        "status_view": ("FINAL" if pending_count == 0 else "PENDING_CLASSIFICATION"),
        "warnings": [
            ("No unresolved investment balance is included in " "the SOTP equity bridge."),
            (
                "Pending investment exposure is informational and "
                "must not be treated as an additive adjustment."
            ),
            ("Component balances are explicitly excluded to " "prevent double counting."),
        ],
    }
