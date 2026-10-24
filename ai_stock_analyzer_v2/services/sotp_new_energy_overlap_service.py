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


def analyze_sotp_new_energy_overlap(
    symbol: str,
) -> dict[str, Any]:

    # ----------------------------------------------------
    # LOAD FACTUAL NEW ENERGY DATA
    # ----------------------------------------------------

    data = get_sotp_new_energy_data(symbol)

    if data.get("status") != "OK":
        return data

    net_assets = data.get(
        "reported_net_assets",
        {},
    )

    rne = _num(net_assets.get("reliance_new_energy"))

    rnse = _num(net_assets.get("reliance_new_solar_energy"))

    rnebs = _num(net_assets.get("reliance_new_energy_battery_storage"))

    values = {
        "reliance_new_energy": rne,
        "reliance_new_solar_energy": rnse,
        "reliance_new_energy_battery_storage": rnebs,
    }

    populated_values = [value for value in values.values() if value is not None]

    arithmetic_total = sum(populated_values) if populated_values else None

    # ----------------------------------------------------
    # OVERLAP TESTS
    # ----------------------------------------------------
    #
    # Ownership structure:
    # Confirmed from FY2025-26 annual-report subsidiary
    # ownership disclosures.
    #
    # Consolidation basis:
    # Confirmed because the New Energy entities are
    # reported within the RIL consolidated group.
    #
    # Intercompany overlap:
    # NOT YET RESOLVED.
    #
    # We still need evidence establishing whether the
    # entity-level net asset balances contain investments
    # in, or balances with, other New Energy entities.
    #
    # Therefore the arithmetic total must NOT yet be used
    # as an additive New Energy valuation.
    # ----------------------------------------------------

    ownership_structure_confirmed = True

    consolidation_basis_confirmed = True

    intercompany_overlap_resolved = False

    additive_net_assets_confirmed = (
        ownership_structure_confirmed
        and consolidation_basis_confirmed
        and intercompany_overlap_resolved
    )

    # ----------------------------------------------------
    # UNRESOLVED TESTS
    # ----------------------------------------------------

    unresolved_tests = []

    if not ownership_structure_confirmed:
        unresolved_tests.append("OWNERSHIP_STRUCTURE")

    if not consolidation_basis_confirmed:
        unresolved_tests.append("CONSOLIDATION_BASIS")

    if not intercompany_overlap_resolved:
        unresolved_tests.append("INTERCOMPANY_OVERLAP")

    # ----------------------------------------------------
    # VALUATION / OVERLAP POLICY
    # ----------------------------------------------------

    if additive_net_assets_confirmed:

        authorized_net_asset_value = arithmetic_total

        treatment = "AUTHORIZED_NET_ASSET_VALUE"

        status_view = "OVERLAP_RESOLVED"

    else:

        authorized_net_asset_value = None

        if not ownership_structure_confirmed:

            treatment = "DIAGNOSTIC_ONLY_PENDING_" "OWNERSHIP_REVIEW"

            status_view = "OWNERSHIP_STRUCTURE_UNRESOLVED"

        elif not consolidation_basis_confirmed:

            treatment = "DIAGNOSTIC_ONLY_PENDING_" "CONSOLIDATION_REVIEW"

            status_view = "CONSOLIDATION_BASIS_UNRESOLVED"

        elif not intercompany_overlap_resolved:

            treatment = "DIAGNOSTIC_ONLY_PENDING_" "INTERCOMPANY_OVERLAP_REVIEW"

            status_view = "INTERCOMPANY_OVERLAP_UNRESOLVED"

        else:

            treatment = "DIAGNOSTIC_ONLY"

            status_view = "OVERLAP_REVIEW_REQUIRED"

    # ----------------------------------------------------
    # RETURN
    # ----------------------------------------------------

    return {
        "status": "OK",
        "version": "V5.0",
        "symbol": data.get("symbol"),
        "segment": "New Energy",
        "currency": data.get("currency"),
        "unit": data.get("unit"),
        "source": data.get("source"),
        "source_period": data.get("source_period"),
        # ------------------------------------------------
        # REPORTED NET ASSETS
        # ------------------------------------------------
        "reported_net_assets": values,
        "arithmetic_total": (round(arithmetic_total, 2) if arithmetic_total is not None else None),
        "arithmetic_total_is_additive": (additive_net_assets_confirmed),
        # ------------------------------------------------
        # OWNERSHIP EVIDENCE
        # ------------------------------------------------
        "ownership_evidence": {
            "reliance_new_energy": 1.0,
            "reliance_new_solar_energy": 1.0,
            "reliance_new_energy_battery_storage": 1.0,
            "ownership_basis": ("FY2025-26 annual report subsidiary " "ownership disclosure"),
            "ownership_confirmed": (ownership_structure_confirmed),
        },
        # ------------------------------------------------
        # CONSOLIDATION EVIDENCE
        # ------------------------------------------------
        "consolidation_evidence": {
            "ril_consolidated_reporting": True,
            "wholly_owned_subsidiaries": True,
            "entity_level_net_assets_reported": True,
            "consolidation_basis_confirmed": (consolidation_basis_confirmed),
            "entity_relationships_fully_mapped": False,
            "intercompany_investments_identified": False,
            "intercompany_eliminations_quantified": False,
            "basis": (
                "FY2025-26 annual report provides "
                "consolidated RIL reporting and "
                "subsidiary-level New Energy disclosures. "
                "The consolidation basis is therefore "
                "confirmed, while economic intercompany "
                "overlap remains subject to separate "
                "review."
            ),
        },
        # ------------------------------------------------
        # INTERCOMPANY EVIDENCE
        # ------------------------------------------------
        "intercompany_evidence": {
            "rne_net_assets": rne,
            "rnse_net_assets": rnse,
            "rnebs_net_assets": rnebs,
            "entity_level_balances_available": all(
                value is not None for value in [rne, rnse, rnebs]
            ),
            "ownership_structure_confirmed": (ownership_structure_confirmed),
            "consolidation_basis_confirmed": (consolidation_basis_confirmed),
            "direct_parent_child_investments_quantified": (False),
            "intercompany_balances_quantified": False,
            "intercompany_eliminations_quantified": False,
            "economic_additivity_established": (intercompany_overlap_resolved),
            "evidence_status": (
                "RESOLVED" if intercompany_overlap_resolved else "INTERCOMPANY_DATA_REQUIRED"
            ),
            "basis": (
                "Entity-level New Energy net asset "
                "balances, ownership and consolidation "
                "basis are available. However, the "
                "current dataset does not yet quantify "
                "parent-child investments, intercompany "
                "balances or eliminations required to "
                "establish economic additivity."
            ),
        },
        # ------------------------------------------------
        # OVERLAP TESTS
        # ------------------------------------------------
        "overlap_tests": {
            "ownership_structure_confirmed": (ownership_structure_confirmed),
            "consolidation_basis_confirmed": (consolidation_basis_confirmed),
            "intercompany_overlap_resolved": (intercompany_overlap_resolved),
        },
        "unresolved_tests": unresolved_tests,
        "unresolved_test_count": len(unresolved_tests),
        # ------------------------------------------------
        # VALUATION AUTHORIZATION
        # ------------------------------------------------
        "additive_net_assets_confirmed": (additive_net_assets_confirmed),
        "authorized_net_asset_value": (authorized_net_asset_value),
        "valuation_floor_authorized": (authorized_net_asset_value is not None),
        "treatment": treatment,
        "status_view": status_view,
        # ------------------------------------------------
        # INTERPRETATION
        # ------------------------------------------------
        "interpretation": (
            "Ownership and consolidation basis for the "
            "identified New Energy entities have been "
            "confirmed. Intercompany economic overlap "
            "remains unresolved. The reported entity-level "
            "net asset balances therefore cannot yet be "
            "assumed to be additive, and the arithmetic "
            "total is not authorized as a New Energy "
            "valuation floor."
        ),
        # ------------------------------------------------
        # WARNINGS
        # ------------------------------------------------
        "warnings": [
            (
                "Ownership and consolidation basis are "
                "confirmed, but economic additivity is "
                "not yet established."
            ),
            (
                "The arithmetic sum of reported New "
                "Energy net assets must not be used as "
                "enterprise value or an asset floor."
            ),
            (
                "Parent-child investments or other "
                "intercompany balances may create "
                "double counting."
            ),
            (
                "Intercompany overlap must be resolved "
                "before a net-asset valuation is "
                "authorized."
            ),
        ],
    }
