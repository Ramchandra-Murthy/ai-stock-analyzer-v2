from __future__ import annotations

from typing import Any

from services.sotp_long_term_equity_entity_data_service import (
    get_sotp_long_term_equity_entity_data,
)


def _num(value: Any):
    """
    Convert a value to float when possible.
    Return None for missing, invalid or NaN values.
    """

    try:
        if value is None:
            return None

        value = float(value)

        if value != value:
            return None

        return value

    except (TypeError, ValueError):
        return None


def reconcile_sotp_long_term_equity_entities(
    symbol: str,
) -> dict[str, Any]:
    """
    Evaluate entity-level evidence for Reliance's
    Long-Term Equity Investment pool.

    IMPORTANT:

    Annexure A 'Amount of Investment' disclosures are
    treated as entity-level evidence.

    They are NOT assumed to be directly comparable with
    the consolidated Long-Term Equity Investment carrying
    balance unless the entity data service explicitly
    marks them as comparable.

    Therefore this service separates:

        1. disclosed entity amounts
        2. comparable accounting amounts
        3. entity-population completeness
        4. classification completeness
        5. bridge authorization

    No unresolved amount is authorized for inclusion in
    SOTP equity value.
    """

    # ------------------------------------------------------
    # 1. NORMALIZE SYMBOL
    # ------------------------------------------------------

    symbol = str(symbol or "").upper().strip()

    if symbol.endswith(".NS"):
        symbol = symbol[:-3]

    # ------------------------------------------------------
    # 2. LOAD ENTITY EVIDENCE
    # ------------------------------------------------------

    data = get_sotp_long_term_equity_entity_data(symbol)

    if not isinstance(data, dict) or data.get("status") != "OK":
        return {
            "status": "UNAVAILABLE",
            "version": "V5.0",
            "symbol": symbol,
            "message": ("Long-term equity entity data is unavailable."),
            "source_data": data,
        }

    reported_aggregate = _num(data.get("reported_long_term_equity_investment")) or 0.0

    entities = data.get("entities", [])

    if not isinstance(entities, list):
        entities = []

    # ------------------------------------------------------
    # 3. ENTITY EVIDENCE COUNTS
    # ------------------------------------------------------

    captured_disclosed_amount = 0.0
    comparable_entity_value = 0.0

    valued_entity_count = 0
    comparable_entity_count = 0
    unresolved_entity_count = 0

    for entity in entities:

        if not isinstance(entity, dict):
            continue

        value = _num(entity.get("reported_investment_value"))

        # ----------------------------------------------
        # Annexure / entity disclosed amount
        # ----------------------------------------------

        if value is not None:
            captured_disclosed_amount += value
            valued_entity_count += 1

        # ----------------------------------------------
        # Accounting-basis comparability
        # ----------------------------------------------

        comparable = entity.get("comparable_to_consolidated_carrying_value") is True

        if value is not None and comparable:
            comparable_entity_value += value
            comparable_entity_count += 1

        # ----------------------------------------------
        # Economic classification
        # ----------------------------------------------

        if entity.get("classification") in (
            None,
            "UNRESOLVED",
        ):
            unresolved_entity_count += 1

    # ------------------------------------------------------
    # 4. DISCLOSURE RATIO
    # ------------------------------------------------------
    #
    # This ratio is informational only.
    #
    # It must NOT be interpreted as accounting carrying
    # value coverage because the measurement bases may
    # differ.
    # ------------------------------------------------------

    if reported_aggregate > 0:
        disclosed_amount_ratio = captured_disclosed_amount / reported_aggregate
    else:
        disclosed_amount_ratio = 0.0

    # ------------------------------------------------------
    # 5. MEASUREMENT-BASIS CONTROL
    # ------------------------------------------------------

    measurement_basis_comparable = comparable_entity_count > 0

    # Only calculate an accounting reconciliation gap
    # when comparable entity-level carrying values exist.

    if measurement_basis_comparable:

        reconciliation_gap = reported_aggregate - comparable_entity_value

        accounting_reconciles = abs(reconciliation_gap) <= 1.0

    else:

        reconciliation_gap = None
        accounting_reconciles = False

    # ------------------------------------------------------
    # 6. ENTITY POPULATION
    # ------------------------------------------------------

    entity_population_complete = bool(data.get("entity_level_holdings_complete"))

    # ------------------------------------------------------
    # 7. CLASSIFICATION COMPLETENESS
    # ------------------------------------------------------

    classification_complete = entity_population_complete and unresolved_entity_count == 0

    # ------------------------------------------------------
    # 8. BRIDGE AUTHORIZATION
    # ------------------------------------------------------

    bridge_ready = (
        entity_population_complete
        and measurement_basis_comparable
        and accounting_reconciles
        and classification_complete
    )

    # ------------------------------------------------------
    # 9. STATUS
    # ------------------------------------------------------

    if bridge_ready:

        status_view = "RECONCILED_AND_CLASSIFIED"

    elif not entity_population_complete:

        status_view = "PENDING_ENTITY_POPULATION"

    elif not measurement_basis_comparable:

        status_view = "PENDING_MEASUREMENT_BASIS"

    elif not accounting_reconciles:

        status_view = "PENDING_ACCOUNTING_RECONCILIATION"

    elif not classification_complete:

        status_view = "PENDING_ENTITY_CLASSIFICATION"

    else:

        status_view = "PENDING_REVIEW"

    # ------------------------------------------------------
    # 10. OUTPUT
    # ------------------------------------------------------

    return {
        "status": "OK",
        "version": "V5.0",
        "symbol": symbol,
        "period": data.get("period"),
        "currency": data.get(
            "currency",
            "INR",
        ),
        "unit": data.get(
            "unit",
            "crore",
        ),
        # ----------------------------------------------
        # Controlling accounting aggregate
        # ----------------------------------------------
        "reported_long_term_equity_investment": round(
            reported_aggregate,
            2,
        ),
        # ----------------------------------------------
        # Entity disclosure evidence
        # ----------------------------------------------
        "captured_disclosed_amount": round(
            captured_disclosed_amount,
            2,
        ),
        "disclosed_amount_ratio": round(
            disclosed_amount_ratio,
            4,
        ),
        "disclosed_amount_ratio_percent": round(
            disclosed_amount_ratio * 100.0,
            2,
        ),
        "disclosed_amount_ratio_is_accounting_coverage": False,
        # ----------------------------------------------
        # Comparable accounting evidence
        # ----------------------------------------------
        "comparable_entity_value": round(
            comparable_entity_value,
            2,
        ),
        "comparable_entity_count": (comparable_entity_count),
        "measurement_basis": {
            "entity_amount_basis": ("ANNEXURE_A_AMOUNT_OF_INVESTMENT"),
            "aggregate_basis": ("CONSOLIDATED_ASSOCIATE_JV_INVESTMENT_BALANCE"),
            "comparable": (measurement_basis_comparable),
        },
        # ----------------------------------------------
        # Accounting reconciliation
        # ----------------------------------------------
        "reconciliation_gap": (
            round(reconciliation_gap, 2) if reconciliation_gap is not None else None
        ),
        "accounting_reconciles": (accounting_reconciles),
        # ----------------------------------------------
        # Entity statistics
        # ----------------------------------------------
        "entity_count": len(entities),
        "valued_entity_count": (valued_entity_count),
        "unresolved_entity_count": (unresolved_entity_count),
        # ----------------------------------------------
        # Completion controls
        # ----------------------------------------------
        "entity_population_complete": (entity_population_complete),
        "classification_complete": (classification_complete),
        "bridge_ready": bridge_ready,
        # ----------------------------------------------
        # Authorization tests
        # ----------------------------------------------
        "authorization_tests": {
            "entity_population_complete": (entity_population_complete),
            "measurement_basis_comparable": (measurement_basis_comparable),
            "aggregate_reconciles": (accounting_reconciles),
            "classification_complete": (classification_complete),
        },
        # ----------------------------------------------
        # SOTP treatment
        # ----------------------------------------------
        "sotp_adjustment": {
            "included_value": 0.0,
            "pending_value": round(
                reported_aggregate,
                2,
            ),
            "treatment": "DO_NOT_ADD_YET",
        },
        "status_view": status_view,
        # ----------------------------------------------
        # Interpretation
        # ----------------------------------------------
        "interpretation": (
            "Entity-level Annexure A investment amounts "
            "are retained as disclosure evidence but are "
            "not assumed to be directly comparable with "
            "the consolidated Long-Term Equity Investment "
            "carrying balance. Accounting reconciliation "
            "is therefore deferred until comparable "
            "entity-level carrying-value evidence is "
            "available."
        ),
        "warnings": [
            ("The disclosed amount ratio is not " "accounting carrying-value coverage."),
            (
                "Annexure A investment amounts must not "
                "be forced to reconcile to the consolidated "
                "Long-Term Equity Investment balance."
            ),
            (
                "Entity population completeness and "
                "measurement-basis comparability are "
                "separate authorization tests."
            ),
            (
                "Operating overlap and valuation basis "
                "must still be resolved before any "
                "incremental investment value enters SOTP."
            ),
            (
                "No long-term equity investment may enter "
                "the equity bridge while bridge_ready "
                "is false."
            ),
        ],
        "source_data": data,
    }
