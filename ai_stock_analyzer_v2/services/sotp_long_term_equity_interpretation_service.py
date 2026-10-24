from __future__ import annotations

"""
==========================================================
LONG-TERM EQUITY CLASSIFICATION BRIDGE
Stage   : 13C.1
Version : V5.0
Status  : FROZEN
==========================================================

Purpose
-------
Bridge between:
    Entity Data Service
    Economic Evidence Service

This service DOES NOT:
    - classify entities
    - value entities
    - compute SOTP

It only transports and validates evidence.

Future classification logic belongs in:
    sotp_long_term_equity_interpretation_service.py
"""

from typing import Any

from services.sotp_long_term_equity_economic_evidence_service import (
    get_sotp_long_term_equity_economic_evidence,
)
from services.sotp_long_term_equity_entity_data_service import (
    get_sotp_long_term_equity_entity_data,
)

# ==========================================================
# SHARED CONSTANTS & DOMAIN TYPES
# ==========================================================
BRIDGE_STAGE = "13C.1"
STAGE_13C_1_ID = "STAGE_13C_1"
CLASSIFICATION_VERSION = "V5.0"
EXPECTED_ENTITY_COUNT = 58

STATUS_UNRESOLVED = "UNRESOLVED"
STATUS_RESOLVED = "RESOLVED"

CATEGORY_OPERATING_ASSOCIATE = "OPERATING_ASSOCIATE"
CATEGORY_STRATEGIC_INVESTMENT = "STRATEGIC_INVESTMENT"
CATEGORY_FINANCIAL_INVESTMENT = "FINANCIAL_INVESTMENT"
CATEGORY_INFRASTRUCTURE_INVESTMENT = "INFRASTRUCTURE_INVESTMENT"
CATEGORY_JOINT_OPERATION_EXPOSURE = "JOINT_OPERATION_EXPOSURE"
CATEGORY_OTHER = "OTHER"

OVERLAP_NO = "NO_OVERLAP"
OVERLAP_PARTIAL = "PARTIAL_OVERLAP"
OVERLAP_FULL = "FULL_OVERLAP"

ELIGIBILITY_ELIGIBLE = "ELIGIBLE"
ELIGIBILITY_INELIGIBLE = "INELIGIBLE"
ELIGIBILITY_CONDITIONAL = "CONDITIONAL"

ECONOMIC_CATEGORIES = {
    CATEGORY_OPERATING_ASSOCIATE,
    CATEGORY_STRATEGIC_INVESTMENT,
    CATEGORY_FINANCIAL_INVESTMENT,
    CATEGORY_INFRASTRUCTURE_INVESTMENT,
    CATEGORY_JOINT_OPERATION_EXPOSURE,
    CATEGORY_OTHER,
    STATUS_UNRESOLVED,
}

OVERLAP_STATUSES = {
    OVERLAP_NO,
    OVERLAP_PARTIAL,
    OVERLAP_FULL,
    STATUS_UNRESOLVED,
}

VALUATION_ELIGIBILITY_STATUSES = {
    ELIGIBILITY_ELIGIBLE,
    ELIGIBILITY_INELIGIBLE,
    ELIGIBILITY_CONDITIONAL,
    STATUS_UNRESOLVED,
}

CLASSIFICATION_STATUSES = {
    STATUS_RESOLVED,
    STATUS_UNRESOLVED,
}

EVIDENCE_FIELDS = (
    "business_activity",
    "ril_relationship",
    "relationship_evidence",
    "business_activity_evidence",
    "transaction_evidence",
    "segment_evidence",
    "candidate_operating_segment",
    "operating_overlap_evidence",
    "economic_independence_evidence",
    "valuation_evidence",
    "classification_evidence",
    "source",
    "evidence_complete",
)


def _build_unresolved_classification(
    entity: dict[str, Any],
) -> dict[str, Any]:
    return {
        "note_39_serial": entity.get("note_39_serial"),
        "name": entity.get("name"),
        "country": entity.get("country"),
        "ownership_percent": entity.get("ownership_percent"),
        "operating_segment": None,
        "economic_category": STATUS_UNRESOLVED,
        "operating_overlap": STATUS_UNRESOLVED,
        "overlap_with_segment": None,
        "valuation_eligibility": STATUS_UNRESOLVED,
        "valuation_basis": None,
        "classification_status": STATUS_UNRESOLVED,
        "classification_source": None,
        "classification_reason": None,
        "separate_sotp_value_authorized": False,
    }


def _merge_economic_evidence(
    record: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(record)

    if not isinstance(evidence, dict):
        evidence = {}

    merged["economic_evidence_available"] = bool(evidence)
    merged["economic_evidence_complete"] = bool(evidence.get("evidence_complete"))

    for field in EVIDENCE_FIELDS:
        merged[field] = evidence.get(field)

    # Hard Control: Ingestion layer cannot resolve classification or authorize SOTP bridge values
    merged["classification_status"] = STATUS_UNRESOLVED
    merged["separate_sotp_value_authorized"] = False

    return merged


def _validate_classification_record(
    record: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    if record.get("economic_category") not in ECONOMIC_CATEGORIES:
        errors.append("INVALID_ECONOMIC_CATEGORY")

    if record.get("operating_overlap") not in OVERLAP_STATUSES:
        errors.append("INVALID_OPERATING_OVERLAP")

    if record.get("valuation_eligibility") not in VALUATION_ELIGIBILITY_STATUSES:
        errors.append("INVALID_VALUATION_ELIGIBILITY")

    if record.get("classification_status") not in CLASSIFICATION_STATUSES:
        errors.append("INVALID_CLASSIFICATION_STATUS")

    if record.get("separate_sotp_value_authorized") is not False:
        errors.append(f"SOTP_VALUE_AUTHORIZATION_NOT_ALLOWED_AT_{STAGE_13C_1_ID}")

    return errors


def get_sotp_long_term_equity_classification(
    symbol: str,
) -> dict[str, Any]:
    entity_data = get_sotp_long_term_equity_entity_data(symbol)

    if not isinstance(entity_data, dict) or entity_data.get("status") != "OK":
        return {
            "status": "UNAVAILABLE",
            "version": CLASSIFICATION_VERSION,
            "bridge_stage": BRIDGE_STAGE,
            "symbol": symbol,
            "message": (
                "Long-term equity entity data is unavailable; "
                "economic classification cannot proceed."
            ),
        }

    economic_evidence = get_sotp_long_term_equity_economic_evidence(symbol)

    if not isinstance(economic_evidence, dict) or economic_evidence.get("status") != "OK":
        return {
            "status": "UNAVAILABLE",
            "version": CLASSIFICATION_VERSION,
            "bridge_stage": BRIDGE_STAGE,
            "symbol": entity_data.get("symbol"),
            "message": ("Economic evidence is unavailable; " "classification cannot proceed."),
        }

    population = entity_data.get("population") or []

    # Assertion 1: Validate Population Count against EXPECTED_ENTITY_COUNT
    if len(population) != EXPECTED_ENTITY_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_ENTITY_COUNT} entities, " f"found {len(population)}."
        )

    evidence_entities = economic_evidence.get("entities") or []

    # Assertion 2: Validate Duplicate Names in Economic Evidence
    names = [e.get("name") for e in evidence_entities if isinstance(e, dict)]
    if len(names) != len(set(names)):
        raise RuntimeError("Duplicate entity names detected in economic evidence.")

    evidence_by_name = {
        item.get("name"): item
        for item in evidence_entities
        if isinstance(item, dict) and item.get("name") is not None
    }

    # Assertion 3: Registry Consistency Check
    missing = [
        e["name"]
        for e in population
        if isinstance(e, dict) and e.get("name") not in evidence_by_name
    ]
    if missing:
        raise RuntimeError(f"Economic evidence missing for: {missing}")

    classifications: list[dict[str, Any]] = []

    for entity in population:
        record = _build_unresolved_classification(entity)
        entity_evidence = evidence_by_name.get(entity.get("name"), {})
        record = _merge_economic_evidence(record, entity_evidence)
        classifications.append(record)

    validation_errors: list[dict[str, Any]] = []

    for record in classifications:
        errors = _validate_classification_record(record)
        if errors:
            validation_errors.append(
                {
                    "note_39_serial": record.get("note_39_serial"),
                    "name": record.get("name"),
                    "errors": errors,
                }
            )

    classification_count = len(classifications)
    resolved_count = sum(
        1 for record in classifications if record.get("classification_status") == STATUS_RESOLVED
    )
    unresolved_count = classification_count - resolved_count

    classification_complete = bool(
        entity_data.get("entity_population_complete")
        and classification_count == entity_data.get("population_count")
        and unresolved_count == 0
        and not validation_errors
    )

    # Stage 13C.1 establishes schema only; bridge is explicitly NOT ready
    bridge_ready = False

    return {
        "status": "OK",
        "version": CLASSIFICATION_VERSION,
        "bridge_stage": BRIDGE_STAGE,
        "symbol": entity_data.get("symbol"),
        "period": entity_data.get("period"),
        # Upstream evidence state
        "population_count": entity_data.get("population_count"),
        "population_integrity_valid": entity_data.get("population_integrity_valid"),
        "population_complete": entity_data.get("entity_population_complete"),
        "entity_level_evidence_complete": entity_data.get("entity_level_evidence_complete"),
        # Economic evidence state
        "economic_evidence_registered_count": economic_evidence.get("evidence_registered_count", 0),
        "economic_evidence_complete_count": economic_evidence.get("evidence_complete_count", 0),
        "economic_evidence_all_registered": economic_evidence.get("all_entities_registered", False),
        "economic_evidence_all_complete": economic_evidence.get("all_evidence_complete", False),
        # Classification state
        "classification_count": classification_count,
        "resolved_count": resolved_count,
        "unresolved_count": unresolved_count,
        "classification_complete": classification_complete,
        "validation_error_count": len(validation_errors),
        "validation_errors": validation_errors,
        "classification_records": classifications,
        # SOTP control
        "bridge_ready": bridge_ready,
        "interpretation": (
            "The authoritative Note 39 population and V6 economic evidence have been "
            f"successfully ingested into Stage {BRIDGE_STAGE} classification bridge. All 58 entities "
            f"remain {STATUS_UNRESOLVED} as designed. No separate SOTP value is authorized."
        ),
    }


def audit_classifications() -> None:
    res = get_sotp_long_term_equity_classification("RELIANCE")
    print()
    print(f"Stage {BRIDGE_STAGE} Classification Bridge Audit:")
    print("---------------------------------")
    print(f"Total Registry Entities Ingested : {res.get('classification_count')}")
    print(f"Resolved Count                  : {res.get('resolved_count')}")
    print(f"Unresolved Count                : {res.get('unresolved_count')}")
    print(f"Validation Errors               : {res.get('validation_error_count')}")
    print(f"Bridge Ready                    : {res.get('bridge_ready')}")


if __name__ == "__main__":
    audit_classifications()

    test_result = get_sotp_long_term_equity_classification("RELIANCE")

    assert test_result["status"] == "OK", "Service status should be OK"
    assert (
        test_result["classification_count"] == EXPECTED_ENTITY_COUNT
    ), f"Expected {EXPECTED_ENTITY_COUNT} classification records, got {test_result['classification_count']}"
    assert (
        test_result["unresolved_count"] == EXPECTED_ENTITY_COUNT
    ), f"Expected {EXPECTED_ENTITY_COUNT} unresolved records, got {test_result['unresolved_count']}"
    assert test_result["resolved_count"] == 0, "Expected resolved_count == 0"
    assert test_result["validation_error_count"] == 0, "Expected 0 validation errors"
    assert (
        test_result["bridge_ready"] is False
    ), f"Expected bridge_ready == False in Stage {BRIDGE_STAGE}"
    assert (
        "classification_records" in test_result
    ), "Expected 'classification_records' key in output"

    print(
        f"\nStage {BRIDGE_STAGE} Self-Test Passed: All {EXPECTED_ENTITY_COUNT} unresolved records validated."
    )
