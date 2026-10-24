from __future__ import annotations

from typing import Any

from services.sotp_new_energy_data_service import (
    get_sotp_new_energy_data,
)
from services.sotp_new_energy_overlap_service import (
    analyze_sotp_new_energy_overlap,
)
from services.sotp_new_energy_policy_service import (
    generate_sotp_new_energy_policy,
)


def _num(value):
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def value_sotp_new_energy(
    symbol: str,
) -> dict[str, Any]:

    data = get_sotp_new_energy_data(symbol)
    overlap = analyze_sotp_new_energy_overlap(symbol)
    policy = generate_sotp_new_energy_policy(symbol)

    if data.get("status") != "OK":
        return data

    # ----------------------------------------------------
    # FACTUAL EVIDENCE
    # ----------------------------------------------------

    investment = data.get("investment", {})
    financials = data.get("financials", {})

    announced_investment = _num(investment.get("announced_investment"))

    committed_investment = _num(investment.get("committed_investment"))

    revenue = _num(financials.get("revenue"))
    ebitda = _num(financials.get("ebitda"))
    capital_employed = _num(financials.get("capital_employed"))

    # ----------------------------------------------------
    # OVERLAP-CONTROLLED NET ASSET VALUE
    # ----------------------------------------------------

    authorized_net_asset_value = _num(overlap.get("authorized_net_asset_value"))

    net_asset_authorized = (
        overlap.get("valuation_floor_authorized") is True and authorized_net_asset_value is not None
    )

    # ----------------------------------------------------
    # POLICY-CONTROLLED METHODS
    # ----------------------------------------------------

    authorized_methods = policy.get(
        "authorized_methods",
        [],
    )

    # ----------------------------------------------------
    # METHOD CANDIDATES
    # ----------------------------------------------------

    candidates = {}

    if "NET_ASSET" in authorized_methods and net_asset_authorized:
        candidates["NET_ASSET"] = {
            "value": authorized_net_asset_value,
            "authorized": True,
        }

    # Future methods:
    #
    # EV_REVENUE
    # EV_EBITDA
    # CAPITAL_EMPLOYED
    # CAPACITY_VALUE
    # STRATEGIC_VALUE

    # ----------------------------------------------------
    # FINAL AUTHORIZATION
    # ----------------------------------------------------

    authorized_candidates = {
        method: result
        for method, result in candidates.items()
        if result.get("authorized") is True and result.get("value") is not None
    }

    if authorized_candidates:
        selected_method = next(iter(authorized_candidates))

        enterprise_value = authorized_candidates[selected_method]["value"]

        valuation_ready = True
        status_view = "VALUATION_AUTHORIZED"

    else:
        selected_method = None
        enterprise_value = None
        valuation_ready = False
        status_view = "VALUATION_NOT_AUTHORIZED"

    return {
        "status": "OK",
        "version": "V5.0",
        "symbol": data.get("symbol"),
        "segment": "New Energy",
        "currency": data.get("currency"),
        "unit": data.get("unit"),
        "evidence": {
            "announced_investment": announced_investment,
            "committed_investment": committed_investment,
            "revenue": revenue,
            "ebitda": ebitda,
            "capital_employed": capital_employed,
            "authorized_net_asset_value": (authorized_net_asset_value),
        },
        "overlap_control": {
            "net_asset_authorized": (net_asset_authorized),
            "status_view": overlap.get("status_view"),
            "unresolved_tests": overlap.get(
                "unresolved_tests",
                [],
            ),
        },
        "policy_control": {
            "authorized_methods": (authorized_methods),
            "valuation_ready": policy.get("valuation_ready"),
        },
        "method_candidates": candidates,
        "selected_method": selected_method,
        "enterprise_value": enterprise_value,
        "valuation_ready": valuation_ready,
        "status_view": status_view,
        "interpretation": (
            "New Energy valuation is authorized only "
            "when a valuation method has sufficient "
            "factual evidence, passes overlap controls, "
            "and is explicitly authorized by policy."
        ),
        "warnings": [
            ("Investment commitments are not treated " "as enterprise value."),
            ("Unresolved entity-level net asset " "overlap cannot enter valuation."),
            ("Planned capacity is not valued without " "explicit economic assumptions."),
        ],
    }
