"""
==========================================================
SUM-OF-THE-PARTS (SOTP) AGGREGATION SERVICE
Stage   : 14 (SOTP Aggregation)
Version : V1.2 (Frozen Architecture)
==========================================================

Purpose
-------
Aggregates individual entity valuation records into the consolidated
Sum-of-the-Parts (SOTP) Enterprise Value, Financial Adjustments,
Equity Value, Intrinsic Value, and Intrinsic Value Per Share.

Flow
----
58 Valuation Records (Validated Population)
        │
        ▼
Eligible Investments (separate_sotp_value_authorized == True)
        │
        ▼
Enterprise Value (Σ EV)
        │
        ▼
Cash Adjustment (+ Σ Cash)
        │
        ▼
Debt Adjustment (- Σ Debt)
        │
        ▼
Minority Interest (- Σ Minority Interest)
        │
        ▼
Equity Value
        │
        ▼
Intrinsic Value
        │
        ▼
Intrinsic Value / Share
"""

from typing import Any

from services.sotp_clock import get_current_timestamp
from services.sotp_long_term_equity_valuation_service import (
    get_sotp_long_term_equity_valuation,
)

from services.sotp_long_term_equity_domain_constants import (
    DEFAULT_PARENT_SHARES_OUTSTANDING_MILLIONS,
    EXPECTED_ENTITY_COUNT,
    STATUS_OK,
    STATUS_UNAVAILABLE,
)

# ==========================================================
# 1. Single-Responsibility Helper Functions
# ==========================================================


def _get_authorized_entities(
    valuation_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Filters valuation records to only authorized SOTP components."""
    return [
        record
        for record in valuation_records
        if record.get("separate_sotp_value_authorized") is True
    ]


def _compute_enterprise_value(eligible_records: list[dict[str, Any]]) -> float:
    """Computes total Enterprise Value across eligible components (nulls treated as 0.0)."""
    return sum(float(record.get("enterprise_value") or 0.0) for record in eligible_records)


def _compute_total_cash(eligible_records: list[dict[str, Any]]) -> float:
    """Computes total standalone cash across eligible components."""
    return sum(float(record.get("cash") or 0.0) for record in eligible_records)


def _compute_total_net_debt(eligible_records: list[dict[str, Any]]) -> float:
    """Computes total net debt across eligible components."""
    return sum(float(record.get("net_debt") or 0.0) for record in eligible_records)


def _compute_minority_interest(eligible_records: list[dict[str, Any]]) -> float:
    """Computes total minority interest across eligible components."""
    return sum(float(record.get("minority_interest") or 0.0) for record in eligible_records)


def _compute_equity_value(
    enterprise_value: float,
    cash: float,
    debt: float,
    minority_interest: float,
) -> float:
    """
    Computes Equity Value using standard bridge equation:
    Equity Value = Enterprise Value + Cash - Debt - Minority Interest
    """
    return enterprise_value + cash - debt - minority_interest


def _compute_intrinsic_value(equity_value: float, holding_discount_pct: float = 0.0) -> float:
    """
    Computes Intrinsic Value from Equity Value.
    Allows for future holding company / cross-holding adjustments.
    """
    return equity_value * (1.0 - holding_discount_pct)


def _compute_value_per_share(
    intrinsic_value: float,
    shares_outstanding_millions: float = DEFAULT_PARENT_SHARES_OUTSTANDING_MILLIONS,
) -> float:
    """Computes Intrinsic Value Per Share."""
    if shares_outstanding_millions <= 0:
        return 0.0
    return intrinsic_value / shares_outstanding_millions


def _generate_breakdown(eligible_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Generates a structured component breakdown for audit and research reporting.
    Preserves framework/model completion status and normalizes missing numbers to 0.0.
    """
    breakdown = []
    for record in eligible_records:
        ev = float(record.get("enterprise_value") or 0.0)
        eq = float(record.get("equity_value") or 0.0)
        nd = float(record.get("net_debt") or 0.0)
        mi = float(record.get("minority_interest") or 0.0)
        # Use truthiness to preserve every nonzero float, including very small values.
        contrib = ev if ev else eq

        breakdown.append(
            {
                "entity": record.get("name", "UNKNOWN"),
                "classification": record.get("classification"),
                "method": record.get("valuation_method"),
                "status": record.get("valuation_status"),
                "framework_complete": record.get("framework_complete", True),
                "model_complete": record.get("model_complete", False),
                "enterprise_value": ev,
                "equity_value": eq,
                "net_debt": nd,
                "minority_interest": mi,
                "value_contribution": contrib,
            }
        )
    return breakdown


def _validate_sotp(payload: dict[str, Any]) -> bool:
    """Validates SOTP summary keys, numeric types, and structural relationships."""
    required_keys = [
        "enterprise_value",
        "cash",
        "debt",
        "minority_interest",
        "equity_value",
        "intrinsic_value",
        "intrinsic_value_per_share",
        "component_count",
        "total_records_processed",
        "component_breakdown",
    ]
    for key in required_keys:
        if key not in payload:
            return False

    # Structural numeric type checks
    for field in (
        "enterprise_value",
        "equity_value",
        "intrinsic_value",
        "intrinsic_value_per_share",
    ):
        if not isinstance(payload.get(field), (int, float)):
            return False

    # Stronger population and boundary checks
    comp_count = payload["component_count"]
    total_processed = payload["total_records_processed"]
    breakdown = payload["component_breakdown"]

    if comp_count > total_processed:
        return False
    if len(breakdown) != comp_count:
        return False

    return True


def audit_sotp(
    eligible_count: int,
    ev: float,
    equity_val: float,
    intrinsic_val: float,
    error_count: int,
) -> None:
    """Prints standard SOTP Audit summary."""
    print("\n==========================================================")
    print("SOTP Audit")
    print("==========================================================")
    print(f"Eligible Components : {eligible_count}")
    print(f"Enterprise Value    : ${ev:,.2f} M")
    print(f"Equity Value        : ${equity_val:,.2f} M")
    print(f"Intrinsic Value     : ${intrinsic_val:,.2f} M")
    print(f"Errors              : {error_count}")
    print("==========================================================\n")


# ==========================================================
# 2. Main Service Function
# ==========================================================


def get_sotp_long_term_equity_sotp_service(
    symbol: str,
    shares_outstanding_millions: float = DEFAULT_PARENT_SHARES_OUTSTANDING_MILLIONS,
) -> dict[str, Any]:
    """
    Main SOTP Aggregation Routine.
    Consumes ONLY get_sotp_long_term_equity_valuation(symbol).
    """
    # 1. Fetch and guard upstream Valuation Service status
    valuation_payload = get_sotp_long_term_equity_valuation(symbol)
    if not isinstance(valuation_payload, dict) or valuation_payload.get("status") != STATUS_OK:
        return {
            "status": STATUS_UNAVAILABLE,
            "symbol": symbol,
            "message": "Valuation service unavailable or returned non-OK status.",
            "aggregation_complete": False,
        }

    all_records = valuation_payload["valuation_records"]

    # 2. Validate expected entity population
    if len(all_records) != EXPECTED_ENTITY_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_ENTITY_COUNT} valuation records, " f"found {len(all_records)}."
        )

    # 3. Filter authorized components
    eligible_records = _get_authorized_entities(all_records)
    eligible_count = len(eligible_records)

    # 4. Perform financial aggregations & adjustments
    ev = _compute_enterprise_value(eligible_records)
    cash = _compute_total_cash(eligible_records)
    debt = _compute_total_net_debt(eligible_records)
    mi = _compute_minority_interest(eligible_records)

    equity_val = _compute_equity_value(
        enterprise_value=ev,
        cash=cash,
        debt=debt,
        minority_interest=mi,
    )

    intrinsic_val = _compute_intrinsic_value(equity_value=equity_val)
    per_share_val = _compute_value_per_share(
        intrinsic_value=intrinsic_val,
        shares_outstanding_millions=shares_outstanding_millions,
    )

    # 5. Generate component breakdown
    breakdown = _generate_breakdown(eligible_records)

    # 6. Build output payload structure
    timestamp = get_current_timestamp()
    validation_error_count = 0

    sotp_payload = {
        "status": STATUS_OK,
        "symbol": symbol,
        "timestamp": timestamp,
        "component_count": eligible_count,
        "total_records_processed": len(all_records),
        "enterprise_value": ev,
        "cash": cash,
        "debt": debt,
        "minority_interest": mi,
        "equity_value": equity_val,
        "intrinsic_value": intrinsic_val,
        "intrinsic_value_per_share": per_share_val,
        "shares_outstanding_millions": shares_outstanding_millions,
        "component_breakdown": breakdown,
        "validation_error_count": validation_error_count,
        "aggregation_complete": True,
    }

    # 7. Validate summary integrity
    if not _validate_sotp(sotp_payload):
        validation_error_count += 1
        sotp_payload["validation_error_count"] = validation_error_count
        sotp_payload["aggregation_complete"] = False

    # 8. Print Audit Output
    audit_sotp(
        eligible_count=eligible_count,
        ev=ev,
        equity_val=equity_val,
        intrinsic_val=intrinsic_val,
        error_count=validation_error_count,
    )

    return sotp_payload


# ==========================================================
# 3. Self-Test Routine
# ==========================================================

if __name__ == "__main__":
    result = get_sotp_long_term_equity_sotp_service("RELIANCE")

    # Required Self-Test Assertions
    assert result["status"] == STATUS_OK, f"Expected {STATUS_OK}, got {result['status']}"
    assert result["aggregation_complete"] is True, "Aggregation stage not marked complete"
    assert (
        result["validation_error_count"] == 0
    ), f"Expected 0 errors, got {result['validation_error_count']}"
    assert (
        result["total_records_processed"] == EXPECTED_ENTITY_COUNT
    ), f"Expected {EXPECTED_ENTITY_COUNT} total records, got {result['total_records_processed']}"

    # Output Schema Verification
    assert "enterprise_value" in result
    assert "cash" in result
    assert "debt" in result
    assert "minority_interest" in result
    assert "equity_value" in result
    assert "intrinsic_value" in result
    assert "intrinsic_value_per_share" in result
    assert "component_breakdown" in result
    assert len(result["component_breakdown"]) == result["component_count"]

    # Component breakdown status check
    sample_item = result["component_breakdown"][0]
    assert "framework_complete" in sample_item
    assert "model_complete" in sample_item

    print("✅ Stage 14 SOTP Aggregation Service frozen and fully verified!")
