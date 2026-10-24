from __future__ import annotations

from typing import Any

from services.sotp_new_energy_data_service import (
    get_sotp_new_energy_data,
)


def _num(value):
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def generate_sotp_new_energy_policy(
    symbol: str,
) -> dict[str, Any]:

    data = get_sotp_new_energy_data(symbol)

    if data.get("status") != "OK":
        return data

    investment = data.get("investment", {})
    assets = data.get("operating_assets", {})
    financials = data.get("financials", {})

    commitment = _num(investment.get("committed_investment"))

    reported_net_asset_total = _num(data.get("reported_net_asset_total"))

    revenue = _num(financials.get("revenue"))
    ebitda = _num(financials.get("ebitda"))
    capital_employed = _num(financials.get("capital_employed"))

    solar = assets.get("solar", {})
    battery = assets.get("battery", {})
    electrolyser = assets.get("electrolyser", {})
    hydrogen = assets.get("green_hydrogen", {})

    # ----------------------------------------------------
    # EVIDENCE TESTS
    # ----------------------------------------------------

    has_commitment = commitment is not None

    has_reported_net_assets = reported_net_asset_total is not None and reported_net_asset_total > 0

    has_operating_financials = any(
        value is not None
        for value in [
            revenue,
            ebitda,
            capital_employed,
        ]
    )

    has_capacity_evidence = any(
        [
            _num(solar.get("planned_capacity_gw")) is not None,
            _num(battery.get("planned_capacity_gwh")) is not None,
            _num(electrolyser.get("planned_capacity_gw")) is not None,
            _num(hydrogen.get("planned_capacity")) is not None,
        ]
    )

    has_commissioned_capacity = any(
        [
            _num(solar.get("commissioned_capacity_gw")) is not None,
            _num(battery.get("commissioned_capacity_gwh")) is not None,
            _num(electrolyser.get("commissioned_capacity_gw")) is not None,
            _num(hydrogen.get("commissioned_capacity")) is not None,
        ]
    )

    # ----------------------------------------------------
    # POLICY
    # ----------------------------------------------------

    policy = {
        "investment_commitment": {
            "value": commitment,
            "classification": ("STRATEGIC_CAPITAL_COMMITMENT"),
            "valuation_treatment": ("DO_NOT_USE_AS_ENTERPRISE_VALUE"),
            "authorized": False,
        },
        "reported_net_assets": {
            "value": reported_net_asset_total,
            "classification": ("ACCOUNTING_NET_ASSET_EVIDENCE"),
            "valuation_treatment": ("PENDING_OVERLAP_REVIEW"),
            "authorized": False,
        },
        "capacity_evidence": {
            "available": has_capacity_evidence,
            "commissioned_capacity_available": (has_commissioned_capacity),
            "classification": ("STRATEGIC_OPERATING_EVIDENCE"),
            "valuation_treatment": ("SUPPORTING_EVIDENCE_ONLY"),
            "authorized": False,
        },
        "operating_financials": {
            "revenue": revenue,
            "ebitda": ebitda,
            "capital_employed": capital_employed,
            "classification": ("OPERATING_VALUATION_INPUT"),
            "valuation_treatment": ("UNAVAILABLE" if not has_operating_financials else "REVIEW"),
            "authorized": False,
        },
    }

    # ----------------------------------------------------
    # VALUATION METHOD READINESS
    # ----------------------------------------------------

    method_readiness = {
        "ev_ebitda": (ebitda is not None and ebitda > 0),
        "ev_revenue": (revenue is not None and revenue > 0),
        "capital_employed_method": (capital_employed is not None and capital_employed > 0),
        "net_asset_method": False,
        "capacity_method": False,
        "strategic_value_method": False,
    }

    authorized_methods = [method for method, ready in method_readiness.items() if ready]

    valuation_ready = len(authorized_methods) > 0

    # ----------------------------------------------------
    # POLICY STATUS
    # ----------------------------------------------------

    if valuation_ready:
        status_view = "VALUATION_METHOD_AVAILABLE"
    elif has_commitment or has_reported_net_assets or has_capacity_evidence:
        status_view = "STRATEGIC_EVIDENCE_AVAILABLE_" "VALUATION_NOT_AUTHORIZED"
    else:
        status_view = "INSUFFICIENT_EVIDENCE"

    return {
        "status": "OK",
        "version": "V5.0",
        "symbol": data.get("symbol"),
        "segment": "New Energy",
        "currency": data.get("currency"),
        "unit": data.get("unit"),
        "source": data.get("source"),
        "source_period": data.get("source_period"),
        "source_reliability": data.get("reliability"),
        "evidence": {
            "investment_commitment_available": (has_commitment),
            "reported_net_assets_available": (has_reported_net_assets),
            "capacity_evidence_available": (has_capacity_evidence),
            "commissioned_capacity_available": (has_commissioned_capacity),
            "operating_financials_available": (has_operating_financials),
        },
        "policy": policy,
        "method_readiness": method_readiness,
        "authorized_methods": authorized_methods,
        "authorized_method_count": len(authorized_methods),
        "valuation_ready": valuation_ready,
        "authorized_strategic_value": None,
        "authorized_enterprise_value": None,
        "status_view": status_view,
        "interpretation": (
            "New Energy has material strategic, capacity "
            "and accounting evidence, but the currently "
            "available factual dataset does not authorize "
            "a standalone enterprise value. Investment "
            "commitments are not enterprise value, "
            "reported subsidiary net assets require "
            "overlap review, and planned capacity requires "
            "a separate economic valuation framework."
        ),
        "warnings": [
            (
                "The disclosed clean-energy investment "
                "commitment must not be used directly as "
                "New Energy enterprise value."
            ),
            (
                "Reported New Energy-related subsidiary "
                "net assets remain diagnostic until "
                "consolidation and ownership overlap are "
                "resolved."
            ),
            (
                "Planned manufacturing capacity does not "
                "authorize a capacity-based valuation "
                "without unit economics and utilization "
                "assumptions."
            ),
            (
                "No strategic New Energy value is "
                "authorized for the SOTP bridge by this "
                "policy service."
            ),
        ],
    }
