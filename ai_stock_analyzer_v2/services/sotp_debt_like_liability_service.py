from __future__ import annotations

from typing import Any

from services.sotp_balance_sheet_detail_service import (
    get_sotp_balance_sheet_details,
)


def _num(value: Any):
    if isinstance(value, (int, float)):
        return float(value)
    return None


def generate_sotp_debt_like_liabilities(
    symbol: str,
) -> dict[str, Any]:
    """
    Identify potential debt-like liabilities for the SOTP EV-to-equity bridge.

    IMPORTANT:
    This service classifies liabilities.
    It does NOT automatically authorize all items for deduction.
    """

    symbol = symbol.upper().strip()

    details = get_sotp_balance_sheet_details(symbol)

    if not isinstance(details, dict):
        return {
            "status": "ERROR",
            "symbol": symbol,
            "message": "Balance-sheet detail service returned invalid data.",
        }

    if details.get("status") != "OK":
        return {
            "status": "ERROR",
            "symbol": symbol,
            "message": "Balance-sheet details are unavailable.",
        }

    debt = details.get("debt", {}) or {}

    total_debt = _num(debt.get("total_debt"))
    lease_obligations = _num(debt.get("capital_lease_obligations"))

    # -----------------------------------------------------
    # RELIANCE FY2025-26 AUDITED SOTP OVERRIDES
    # -----------------------------------------------------

    if symbol in {"RELIANCE", "RELIANCE.NS"}:

        audited_gross_debt = 374421.0
        audited_cash_marketable = 249704.0
        audited_net_debt = 124717.0

        spectrum_liability = 104514.0

        jiostar_onerous_contract = 17742.0
        decommissioning_provision = 2211.0

        liabilities = {
            "audited_net_debt": {
                "value": audited_net_debt,
                "classification": "NET_DEBT",
                "segment": "CONSOLIDATED",
                "treatment": "DEDUCT",
                "bridge_ready": True,
                "reason": ("RIL-reported gross debt less cash and " "marketable securities."),
            },
            "lease_liabilities": {
                "value": lease_obligations,
                "classification": "LEASE_LIABILITY",
                "segment": "CONSOLIDATED",
                "treatment": "REVIEW",
                "bridge_ready": False,
                "reason": (
                    "Requires confirmation of whether lease "
                    "obligations are already reflected in the "
                    "valuation multiple / enterprise-value basis."
                ),
            },
            "spectrum_deferred_payment": {
                "value": spectrum_liability,
                "classification": "DEBT_LIKE_FINANCING",
                "segment": "DIGITAL",
                "treatment": "REVIEW_FOR_DEDUCTION",
                "bridge_ready": False,
                "reason": (
                    "Deferred spectrum auction payments are "
                    "interest-bearing financing obligations "
                    "associated primarily with the Digital/Jio "
                    "business. Separate deduction requires "
                    "confirmation that the Digital EV benchmark "
                    "does not already incorporate equivalent "
                    "obligations."
                ),
            },
            "jiostar_onerous_contract": {
                "value": jiostar_onerous_contract,
                "classification": "OPERATING_OR_CONTRACTUAL_PROVISION",
                "segment": "REVIEW",
                "treatment": "REVIEW",
                "bridge_ready": False,
                "reason": (
                    "Provision should not be treated as financial "
                    "debt without establishing its relationship "
                    "to operating EV and the underlying obligation."
                ),
            },
            "decommissioning_provision": {
                "value": decommissioning_provision,
                "classification": "OPERATING_LONG_TERM_OBLIGATION",
                "segment": "UPSTREAM",
                "treatment": "REVIEW",
                "bridge_ready": False,
                "reason": (
                    "Potential debt-like adjustment for upstream "
                    "valuation, but requires confirmation that "
                    "peer EV metrics and EBITDA valuation do not "
                    "already account for the obligation."
                ),
            },
        }

        authorized_adjustment = -audited_net_debt

        pending_debt_like = spectrum_liability

        return {
            "status": "OK",
            "version": "V5.0",
            "symbol": "RELIANCE",
            "currency": "INR",
            "unit": "crore",
            "audited_capital_structure": {
                "gross_debt": audited_gross_debt,
                "cash_and_marketable_securities": audited_cash_marketable,
                "net_debt": audited_net_debt,
            },
            "liabilities": liabilities,
            "authorized_bridge_adjustment": authorized_adjustment,
            "authorized_deduction": audited_net_debt,
            "pending_debt_like_adjustment": pending_debt_like,
            "bridge_status": "PARTIAL",
            "warnings": [
                (
                    "Only audited net debt is currently authorized "
                    "for deduction from SOTP enterprise value."
                ),
                (
                    "Deferred spectrum liabilities are classified "
                    "as a debt-like candidate but are not yet "
                    "authorized for deduction."
                ),
                (
                    "Lease liabilities must not be deducted "
                    "separately until overlap with the EV and "
                    "multiple definitions is resolved."
                ),
                (
                    "Provisions are not automatically financial "
                    "debt and require obligation-specific review."
                ),
            ],
        }

    # -----------------------------------------------------
    # GENERIC FALLBACK
    # -----------------------------------------------------

    return {
        "status": "PARTIAL",
        "version": "V5.0",
        "symbol": symbol,
        "currency": details.get("currency"),
        "unit": details.get("unit"),
        "liabilities": {
            "total_debt": {
                "value": total_debt,
                "classification": "DEBT",
                "treatment": "REVIEW",
                "bridge_ready": False,
            },
            "lease_liabilities": {
                "value": lease_obligations,
                "classification": "LEASE_LIABILITY",
                "treatment": "REVIEW",
                "bridge_ready": False,
            },
        },
        "authorized_bridge_adjustment": None,
        "bridge_status": "REVIEW_REQUIRED",
        "warnings": ["Audited SOTP liability policy is not configured for this symbol."],
    }
