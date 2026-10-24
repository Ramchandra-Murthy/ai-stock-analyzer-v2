from services.sotp_financial_asset_policy_service import (
    evaluate_financial_asset_policy,
)


def evaluate_financial_asset_overlap(symbol: str) -> dict:
    """
    Determine whether the non-current financial asset pool can
    currently be treated as incremental to operating SOTP value.

    This service does not value the assets. It establishes whether
    available evidence is sufficient to move them into the equity
    bridge.
    """

    policy = evaluate_financial_asset_policy(symbol)

    if not isinstance(policy, dict) or policy.get("status") != "OK":
        return {
            "status": "UNAVAILABLE",
            "symbol": symbol,
            "message": "Financial asset policy is unavailable.",
        }

    assets = policy.get("financial_assets", {})
    reconciliation = policy.get(
        "financial_asset_reconciliation",
        {},
    )

    aggregate = assets.get("aggregate")
    reconciles = reconciliation.get("reconciles", False)

    # ------------------------------------------------------
    # Evidence established so far
    # ------------------------------------------------------

    evidence = {
        "separately_reported_non_current_asset": (isinstance(aggregate, (int, float))),
        "component_reconciliation": bool(reconciles),
        "afs_component_identified": (
            isinstance(
                assets.get("available_for_sale_securities"),
                (int, float),
            )
        ),
        "fvtpl_component_identified": (
            isinstance(
                assets.get("fvtpl_financial_assets"),
                (int, float),
            )
        ),
        "operating_sotp_uses_segment_ebitda": True,
        "non_operating_financial_income_observed": True,
    }

    # ------------------------------------------------------
    # Remaining unresolved questions
    # ------------------------------------------------------

    unresolved = {
        "operating_asset_overlap_confirmed": False,
        "valuation_basis_confirmed": False,
        "asset_level_composition_confirmed": False,
    }

    # Accounting separation is strong, but final inclusion
    # still requires economic classification and valuation.
    candidate_for_addition = all(
        [
            evidence["separately_reported_non_current_asset"],
            evidence["component_reconciliation"],
            evidence["afs_component_identified"],
            evidence["fvtpl_component_identified"],
        ]
    )

    bridge_ready = (
        candidate_for_addition
        and unresolved["operating_asset_overlap_confirmed"]
        and unresolved["valuation_basis_confirmed"]
        and unresolved["asset_level_composition_confirmed"]
    )

    return {
        "status": "OK",
        "symbol": policy.get("symbol", symbol),
        "period": policy.get("period"),
        "currency": policy.get("currency", "INR"),
        "unit": policy.get("unit", "crore"),
        "reported_financial_assets": aggregate,
        "classification": (
            "NON_OPERATING_FINANCIAL_ASSET_CANDIDATE"
            if candidate_for_addition
            else "UNRESOLVED_FINANCIAL_ASSET"
        ),
        "evidence": evidence,
        "unresolved_tests": unresolved,
        "candidate_for_addition": candidate_for_addition,
        "bridge_ready": bridge_ready,
        "sotp_adjustment": {
            "included_value": 0.0,
            "pending_value": (float(aggregate) if isinstance(aggregate, (int, float)) else 0.0),
            "treatment": "PENDING_FINAL_CLASSIFICATION",
        },
        "interpretation": (
            "The non-current financial asset pool is separately "
            "reported and its AFS and FVTPL components reconcile "
            "to the aggregate. The operating SOTP is based on "
            "segment EBITDA, while non-operating financial income "
            "is separately reported in the income statement. "
            "These facts support treatment as a candidate "
            "non-operating asset. Final inclusion remains pending "
            "until economic overlap, asset composition and "
            "valuation basis are established."
        ),
        "warnings": [
            (
                "Candidate-for-addition status does not mean that "
                "the reported carrying value should be added to "
                "SOTP equity value."
            ),
            (
                "The financial asset pool requires asset-level "
                "classification before a valuation adjustment is "
                "authorized."
            ),
        ],
    }
