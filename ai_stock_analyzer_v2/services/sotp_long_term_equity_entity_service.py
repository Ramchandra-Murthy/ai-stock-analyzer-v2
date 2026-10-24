from __future__ import annotations

from typing import Any

from services.sotp_long_term_equity_economic_evidence_service import (
    get_sotp_long_term_equity_economic_evidence,
)
from services.sotp_long_term_equity_entity_data_service import (
    get_sotp_long_term_equity_entity_data,
)
from services.sotp_long_term_equity_overlap_service import (
    evaluate_long_term_equity_overlap,
)
from services.sotp_long_term_equity_reconciliation_service import (
    reconcile_sotp_long_term_equity_entities,
)
from services.sotp_segment_accounting_basis_service import (
    get_sotp_segment_accounting_basis,
)


def _num(value: Any):
    try:
        if value is None:
            return None

        value = float(value)

        if value != value:
            return None

        return value

    except (TypeError, ValueError):
        return None


def classify_long_term_equity_entities(
    symbol: str,
) -> dict[str, Any]:
    """
    Classify entity-level evidence relating to the
    Long-Term Equity Investment pool.

    This service combines:

        1. aggregate accounting hierarchy
        2. entity-level disclosure evidence
        3. measurement-basis reconciliation controls
        4. economic classification controls

    IMPORTANT:

    Entity-level Annexure A investment amounts are
    evidence only.

    They are not treated as consolidated carrying values
    and are not authorized as SOTP fair values.

    No investment enters the equity bridge until:

        - entity population is sufficiently established
        - ownership is established
        - operating overlap is resolved
        - valuation basis is authorized
        - unresolved classifications are eliminated
    """

    # ------------------------------------------------------
    # 1. NORMALIZE SYMBOL
    # ------------------------------------------------------

    base_symbol = str(symbol or "").upper().strip()

    if base_symbol.endswith(".NS"):
        base_symbol = base_symbol[:-3]

    # ------------------------------------------------------
    # 2. AGGREGATE ACCOUNTING OVERLAP
    # ------------------------------------------------------

    overlap = evaluate_long_term_equity_overlap(base_symbol)

    if not isinstance(overlap, dict) or overlap.get("status") != "OK":
        return {
            "status": "UNAVAILABLE",
            "version": "V5.0",
            "symbol": base_symbol,
            "message": ("Long-term equity overlap analysis " "is unavailable."),
            "source_overlap_analysis": overlap,
        }

    # ------------------------------------------------------
    # 3. ENTITY EVIDENCE
    # ------------------------------------------------------

    entity_data = get_sotp_long_term_equity_entity_data(base_symbol)

    if not isinstance(entity_data, dict) or entity_data.get("status") != "OK":
        return {
            "status": "UNAVAILABLE",
            "version": "V5.0",
            "symbol": base_symbol,
            "message": ("Long-term equity entity evidence " "is unavailable."),
            "source_overlap_analysis": overlap,
            "source_entity_data": entity_data,
        }

    # ------------------------------------------------------
    # 4. RECONCILIATION / MEASUREMENT CONTROL
    # ------------------------------------------------------

    reconciliation = reconcile_sotp_long_term_equity_entities(base_symbol)

    if not isinstance(reconciliation, dict) or reconciliation.get("status") != "OK":
        return {
            "status": "UNAVAILABLE",
            "version": "V5.0",
            "symbol": base_symbol,
            "message": ("Entity reconciliation analysis " "is unavailable."),
            "source_overlap_analysis": overlap,
            "source_entity_data": entity_data,
            "source_reconciliation": reconciliation,
        }

    # ------------------------------------------------------
    # ECONOMIC EVIDENCE CONTROL
    # ------------------------------------------------------

    economic_evidence = get_sotp_long_term_equity_economic_evidence(base_symbol)

    if not isinstance(economic_evidence, dict) or economic_evidence.get("status") != "OK":
        return {
            "status": "UNAVAILABLE",
            "version": "V5.0",
            "symbol": base_symbol,
            "message": ("Long-term equity economic evidence " "is unavailable."),
            "source_overlap_analysis": overlap,
            "source_entity_data": entity_data,
            "source_reconciliation": reconciliation,
            "source_economic_evidence": economic_evidence,
        }

    economic_evidence_complete = bool(
        economic_evidence.get(
            "all_evidence_complete",
            False,
        )
    )

    # ------------------------------------------------------
    # 5. ACCOUNTING AGGREGATE
    # ------------------------------------------------------

    reported_value = _num(overlap.get("reported_long_term_equity_investment"))

    components = overlap.get("components", {})

    if not isinstance(components, dict):
        components = {}

    joint_venture_value = _num(components.get("joint_venture_investments"))

    associate_value = _num(components.get("associate_investments"))

    component_total = _num(components.get("component_total"))

    aggregate_reconciles = bool(
        overlap.get("reconciliation", {}).get(
            "reconciles",
            False,
        )
    )

    # ------------------------------------------------------
    # 6. ENTITY POPULATION
    # ------------------------------------------------------

    entities = entity_data.get("entities", [])

    if not isinstance(entities, list):
        entities = []

    entity_level_holdings_available = len(entities) > 0

    entity_population_complete = bool(reconciliation.get("entity_population_complete"))

    # ------------------------------------------------------
    # 7. ENTITY CLASSIFICATION SUMMARY
    # ------------------------------------------------------

    operating_overlap_count = 0
    incremental_investment_count = 0
    component_only_count = 0
    unresolved_entity_count = 0

    operating_overlap_disclosed_amount = 0.0
    incremental_disclosed_amount = 0.0
    component_only_disclosed_amount = 0.0
    unresolved_disclosed_amount = 0.0

    entities_with_ownership = 0
    entities_with_overlap_resolution = 0
    entities_with_valuation_basis = 0

    for entity in entities:

        if not isinstance(entity, dict):
            continue

        classification = entity.get("classification")

        disclosed_amount = _num(entity.get("reported_investment_value"))

        ownership = _num(entity.get("ownership_percent"))

        operating_overlap = entity.get("operating_overlap")

        valuation_basis = entity.get("valuation_basis")

        if ownership is not None:
            entities_with_ownership += 1

        if operating_overlap in (
            True,
            False,
        ):
            entities_with_overlap_resolution += 1

        if valuation_basis not in (
            None,
            "",
            "UNRESOLVED",
        ):
            entities_with_valuation_basis += 1

        if classification == "OPERATING_OVERLAP":

            operating_overlap_count += 1

            if disclosed_amount is not None:
                operating_overlap_disclosed_amount += disclosed_amount

        elif classification == "INCREMENTAL_INVESTMENT":

            incremental_investment_count += 1

            if disclosed_amount is not None:
                incremental_disclosed_amount += disclosed_amount

        elif classification == "COMPONENT_ONLY":

            component_only_count += 1

            if disclosed_amount is not None:
                component_only_disclosed_amount += disclosed_amount

        else:

            unresolved_entity_count += 1

            if disclosed_amount is not None:
                unresolved_disclosed_amount += disclosed_amount

    entity_count = len(entities)

    # ------------------------------------------------------
    # 8. OWNERSHIP CONTROL
    # ------------------------------------------------------
    #
    # Ownership evidence exists for the currently captured
    # entities, but the population itself is incomplete.
    #
    # Therefore ownership_structure_confirmed must remain
    # false at aggregate authorization level.
    # ------------------------------------------------------

    captured_ownership_available = entity_count > 0 and entities_with_ownership == entity_count

    ownership_structure_confirmed = entity_population_complete and captured_ownership_available

    # ------------------------------------------------------
    # 9. SEGMENT ACCOUNTING BASIS
    # ------------------------------------------------------
    #
    # This control determines whether equity-accounted
    # associate/JV earnings are included in or excluded
    # from the segment results used by the SOTP engine.
    #
    # Accounting exclusion does NOT establish entity-level
    # economic independence.
    # ------------------------------------------------------

    accounting_basis = get_sotp_segment_accounting_basis(base_symbol)

    if not isinstance(accounting_basis, dict):
        accounting_basis = {}

    accounting_overlap_cleared = bool(
        accounting_basis.get(
            "operating_overlap_implication",
            {},
        ).get(
            "accounting_overlap_cleared",
            False,
        )
    )

    # ------------------------------------------------------
    # 10. ENTITY-LEVEL ECONOMIC OVERLAP CONTROL
    # ------------------------------------------------------

    captured_overlap_resolved = (
        entity_count > 0 and entities_with_overlap_resolution == entity_count
    )

    operating_segment_overlap_resolved = entity_population_complete and captured_overlap_resolved

    # ------------------------------------------------------
    # 11. VALUATION BASIS CONTROL
    # ------------------------------------------------------

    captured_valuation_basis_complete = (
        entity_count > 0 and entities_with_valuation_basis == entity_count
    )

    valuation_basis_confirmed = entity_population_complete and captured_valuation_basis_complete

    # ------------------------------------------------------
    # 12. MEASUREMENT-BASIS CONTROL
    # ------------------------------------------------------

    measurement_basis = reconciliation.get(
        "measurement_basis",
        {},
    )

    if not isinstance(measurement_basis, dict):
        measurement_basis = {}

    measurement_basis_comparable = bool(
        measurement_basis.get(
            "comparable",
            False,
        )
    )

    # ------------------------------------------------------
    # 13. CLASSIFICATION COMPLETENESS
    # ------------------------------------------------------

    classification_complete = (
        entity_population_complete
        and unresolved_entity_count == 0
        and operating_segment_overlap_resolved
    )

    # ------------------------------------------------------
    # 14. BRIDGE AUTHORIZATION
    # ------------------------------------------------------
    #
    # Even if an entity is eventually classified as an
    # incremental investment, the Annexure A amount is not
    # automatically its authorized SOTP value.
    #
    # Therefore this service does not sum disclosed amounts
    # into authorized_adjustment.
    # ------------------------------------------------------

    bridge_ready = (
        aggregate_reconciles
        and entity_population_complete
        and ownership_structure_confirmed
        and economic_evidence_complete
        and operating_segment_overlap_resolved
        and valuation_basis_confirmed
        and classification_complete
        and unresolved_entity_count == 0
    )

    authorized_adjustment = 0.0

    # ------------------------------------------------------
    # 15. UNRESOLVED TESTS
    # ------------------------------------------------------

    unresolved_tests = []

    if not aggregate_reconciles:
        unresolved_tests.append("AGGREGATE_ACCOUNTING_RECONCILIATION")

    if not entity_level_holdings_available:
        unresolved_tests.append("ENTITY_LEVEL_HOLDINGS")

    if not entity_population_complete:
        unresolved_tests.append("ENTITY_POPULATION_COMPLETE")

    if not ownership_structure_confirmed:
        unresolved_tests.append("OWNERSHIP_STRUCTURE")

    if not economic_evidence_complete:
        unresolved_tests.append("ECONOMIC_EVIDENCE")

    if not operating_segment_overlap_resolved:
        unresolved_tests.append("OPERATING_SEGMENT_OVERLAP")

    if not valuation_basis_confirmed:
        unresolved_tests.append("VALUATION_BASIS")

    if unresolved_entity_count > 0:
        unresolved_tests.append("ENTITY_CLASSIFICATION")

    # ------------------------------------------------------
    # 16. STATUS
    # ------------------------------------------------------

    if bridge_ready:
        status_view = "BRIDGE_READY"

    elif not entity_level_holdings_available:
        status_view = "PENDING_ENTITY_EVIDENCE"

    elif not entity_population_complete:
        status_view = "PENDING_ENTITY_POPULATION"

    elif not operating_segment_overlap_resolved:
        status_view = "PENDING_OPERATING_OVERLAP"

    elif not valuation_basis_confirmed:
        status_view = "PENDING_VALUATION_BASIS"

    elif unresolved_entity_count > 0:
        status_view = "PENDING_ENTITY_CLASSIFICATION"

    else:
        status_view = "PENDING_REVIEW"

    # ------------------------------------------------------
    # 17. OUTPUT
    # ------------------------------------------------------

    return {
        "status": "OK",
        "version": "V5.0",
        "symbol": base_symbol,
        "currency": overlap.get(
            "currency",
            "INR",
        ),
        "unit": overlap.get(
            "unit",
            "crore",
        ),
        "period": overlap.get("period"),
        "reported_long_term_equity_investment": (reported_value),
        "accounting_components": {
            "joint_venture_investments": (joint_venture_value),
            "associate_investments": (associate_value),
            "component_total": (component_total),
            "aggregate_reconciles": (aggregate_reconciles),
        },
        "entity_level_holdings_available": (entity_level_holdings_available),
        "entity_population_complete": (entity_population_complete),
        "entity_count": entity_count,
        "entities": entities,
        "entity_evidence_summary": {
            "entities_with_ownership": (entities_with_ownership),
            "entities_with_overlap_resolution": (entities_with_overlap_resolution),
            "entities_with_valuation_basis": (entities_with_valuation_basis),
            "captured_disclosed_amount": (reconciliation.get("captured_disclosed_amount")),
            "disclosed_amount_ratio_percent": (
                reconciliation.get("disclosed_amount_ratio_percent")
            ),
            "disclosed_amount_ratio_is_accounting_coverage": (False),
        },
        "classification_summary": {
            "operating_overlap_count": (operating_overlap_count),
            "operating_overlap_disclosed_amount": round(
                operating_overlap_disclosed_amount,
                2,
            ),
            "incremental_investment_count": (incremental_investment_count),
            "incremental_disclosed_amount": round(
                incremental_disclosed_amount,
                2,
            ),
            "component_only_count": (component_only_count),
            "component_only_disclosed_amount": round(
                component_only_disclosed_amount,
                2,
            ),
            "unresolved_entity_count": (unresolved_entity_count),
            "unresolved_disclosed_amount": round(
                unresolved_disclosed_amount,
                2,
            ),
        },
        "measurement_basis": (measurement_basis),
        "accounting_overlap_cleared": (accounting_overlap_cleared),
        "authorization_tests": {
            "aggregate_reconciles": (aggregate_reconciles),
            "entity_level_holdings_available": (entity_level_holdings_available),
            "entity_population_complete": (entity_population_complete),
            "ownership_structure_confirmed": (ownership_structure_confirmed),
            "accounting_overlap_cleared": (accounting_overlap_cleared),
            "economic_evidence_complete": (economic_evidence_complete),
            "operating_segment_overlap_resolved": (operating_segment_overlap_resolved),
            "valuation_basis_confirmed": (valuation_basis_confirmed),
            "classification_complete": (classification_complete),
            "measurement_basis_comparable": (measurement_basis_comparable),
        },
        "classification_complete": (classification_complete),
        "bridge_ready": bridge_ready,
        "authorized_adjustment": (authorized_adjustment),
        "pending_value": (
            reported_value if reported_value is not None and not bridge_ready else 0.0
        ),
        "unresolved_tests": unresolved_tests,
        "unresolved_test_count": len(unresolved_tests),
        "status_view": status_view,
        "interpretation": (
            "The JV and associate accounting components "
            "reconcile to the Long-Term Equity Investment "
            "aggregate. Entity-level disclosure evidence "
            "is now available, but the captured population "
            "is incomplete. Annexure A investment amounts "
            "are retained as evidence and are not treated "
            "as consolidated carrying values or authorized "
            "SOTP fair values. Ownership, operating overlap "
            "and valuation basis must be resolved across "
            "the complete entity population before any "
            "incremental investment value can enter the "
            "equity bridge."
        ),
        "warnings": [
            (
                "The reported Long-Term Equity Investment "
                "aggregate must not be added directly to "
                "SOTP equity value."
            ),
            ("JV and associate aggregate components " "must not be added separately."),
            (
                "Annexure A disclosed investment amounts "
                "are not assumed to equal consolidated "
                "carrying values."
            ),
            ("The disclosed amount ratio is not " "accounting coverage."),
            (
                "An associate or JV may already be "
                "represented in operating segment economics "
                "and therefore create double counting."
            ),
            (
                "Entity classification does not authorize "
                "use of an accounting or disclosed amount "
                "as SOTP fair value."
            ),
        ],
        "source_overlap_analysis": overlap,
        "source_entity_data": entity_data,
        "source_reconciliation": reconciliation,
        "source_segment_accounting_basis": accounting_basis,
        "source_economic_evidence": economic_evidence,
    }
