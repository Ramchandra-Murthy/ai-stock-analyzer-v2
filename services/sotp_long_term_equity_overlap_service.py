from services.sotp_investment_classification_service import (
    classify_sotp_investment_assets,
)


def _safe_float(value):
    try:
        if value is None:
            return None

        value = float(value)

        if value != value:
            return None

        return value

    except (TypeError, ValueError):
        return None


def evaluate_long_term_equity_overlap(symbol: str) -> dict:
    """
    Evaluate whether the reported Long-Term Equity Investment
    balance can be treated as incremental to operating SOTP EV.

    Current evidence establishes the accounting hierarchy:

        Long-Term Equity Investment
            = JV Investments
            + Associate Investments

    However, accounting reconciliation alone does not establish
    economic independence from businesses already captured in
    the operating SOTP valuation.

    Therefore this service must not authorize the asset until
    entity-level holdings and operating overlap are established.
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

    long_term = assets.get(
        "long_term_equity_investment",
        {},
    )

    joint_venture = assets.get(
        "joint_venture_investments",
        {},
    )

    associate = assets.get(
        "associate_investments",
        {},
    )

    if not isinstance(long_term, dict):
        long_term = {}

    if not isinstance(joint_venture, dict):
        joint_venture = {}

    if not isinstance(associate, dict):
        associate = {}

    long_term_value = _safe_float(long_term.get("value"))

    joint_venture_value = _safe_float(joint_venture.get("value"))

    associate_value = _safe_float(associate.get("value"))

    # ------------------------------------------------------
    # ACCOUNTING RECONCILIATION
    # ------------------------------------------------------

    component_total = None
    reconciliation_gap = None
    reconciles = False

    if joint_venture_value is not None and associate_value is not None:
        component_total = joint_venture_value + associate_value

    if long_term_value is not None and component_total is not None:
        reconciliation_gap = long_term_value - component_total

        reconciles = abs(reconciliation_gap) <= 1.0

    # ------------------------------------------------------
    # EVIDENCE
    # ------------------------------------------------------

    evidence = {
        "aggregate_reported": (long_term_value is not None),
        "joint_venture_component_reported": (joint_venture_value is not None),
        "associate_component_reported": (associate_value is not None),
        "components_reconcile_to_aggregate": (reconciles),
        # Current project does not yet contain
        # entity-level holding information.
        "entity_level_holdings_available": False,
        # Therefore ownership and operating overlap
        # cannot yet be established.
        "ownership_structure_confirmed": False,
        "operating_segment_overlap_resolved": False,
        "valuation_basis_confirmed": False,
    }

    # ------------------------------------------------------
    # UNRESOLVED TESTS
    # ------------------------------------------------------

    unresolved_tests = []

    if not evidence["entity_level_holdings_available"]:
        unresolved_tests.append("ENTITY_LEVEL_HOLDINGS")

    if not evidence["ownership_structure_confirmed"]:
        unresolved_tests.append("OWNERSHIP_STRUCTURE")

    if not evidence["operating_segment_overlap_resolved"]:
        unresolved_tests.append("OPERATING_SEGMENT_OVERLAP")

    if not evidence["valuation_basis_confirmed"]:
        unresolved_tests.append("VALUATION_BASIS")

    # ------------------------------------------------------
    # AUTHORIZATION
    # ------------------------------------------------------

    candidate_for_addition = reconciles and long_term_value is not None

    bridge_ready = candidate_for_addition and len(unresolved_tests) == 0

    authorized_value = long_term_value if bridge_ready else 0.0

    pending_value = (
        0.0 if bridge_ready else (long_term_value if long_term_value is not None else 0.0)
    )

    return {
        "status": "OK",
        "version": "V5.0",
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
        "reported_long_term_equity_investment": (long_term_value),
        "components": {
            "joint_venture_investments": (joint_venture_value),
            "associate_investments": (associate_value),
            "component_total": (component_total),
        },
        "reconciliation": {
            "gap": reconciliation_gap,
            "reconciles": reconciles,
        },
        "classification": (
            "LONG_TERM_EQUITY_ASSET_CANDIDATE"
            if candidate_for_addition
            else "UNRESOLVED_LONG_TERM_EQUITY_ASSET"
        ),
        "evidence": evidence,
        "unresolved_tests": unresolved_tests,
        "unresolved_test_count": len(unresolved_tests),
        "candidate_for_addition": (candidate_for_addition),
        "bridge_ready": bridge_ready,
        "sotp_adjustment": {
            "included_value": authorized_value,
            "pending_value": pending_value,
            "treatment": ("ADD_TO_EQUITY_BRIDGE" if bridge_ready else "DO_NOT_ADD_YET"),
        },
        "status_view": ("AUTHORIZED" if bridge_ready else "PENDING_ENTITY_LEVEL_REVIEW"),
        "interpretation": (
            "JV and associate investment balances "
            "reconcile to the reported Long-Term Equity "
            "Investment aggregate. This establishes the "
            "accounting hierarchy and prevents component "
            "double counting. However, entity-level "
            "holdings, ownership structure, operating "
            "segment overlap and valuation basis are not "
            "yet established. The aggregate therefore "
            "remains excluded from the SOTP equity bridge."
        ),
        "warnings": [
            (
                "JV and associate balances must not be "
                "added separately because they are "
                "components of Long-Term Equity Investment."
            ),
            (
                "Accounting reconciliation does not "
                "establish economic independence from "
                "operating segment enterprise value."
            ),
            (
                "The reported carrying value must not "
                "enter the SOTP equity bridge until "
                "entity-level overlap and valuation basis "
                "are resolved."
            ),
        ],
    }
