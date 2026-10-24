"""
==========================================================
EQUITY RESEARCH REPORT GENERATION SERVICE
Stage   : 16 (Presentation Layer)
Version : V1.2 (Frozen Architecture + Dynamic Segment Risks)
==========================================================

Purpose
-------
Assembles outputs from all prior stages into a comprehensive,
institutional-grade equity research report.

Flow
----
Target Price Service (Stage 15) -> Triggers Full Pipeline Execution
        │
        ▼
Gather Output Payloads (Data, Evidence, Interpretation, Classification, Valuation, SOTP, Target Price)
        │
        ▼
Assemble Report Sections:
  1. Executive Summary
  2. Valuation Summary (Concise Financial Overview Dashboard)
  3. SOTP Financial Bridge
  4. Key Risks & Assumptions (Dynamic Segment Resolution)
  5. Rich Portfolio Appendix
        │
        ▼
Validate Report Completeness & Audit
"""

from typing import Any

from services.sotp_clock import get_current_timestamp
from services.sotp_long_term_equity_report_templates import (
    get_default_risks,
    get_segment_risks,
)
from services.sotp_long_term_equity_sotp_service import (
    get_sotp_long_term_equity_sotp_service,
)
from services.sotp_long_term_equity_target_price_service import (
    get_sotp_long_term_equity_target_price_service,
)

from services.sotp_long_term_equity_domain_constants import (
    EXPECTED_ENTITY_COUNT,
    PIPELINE_VERSION,
    STAGE_16,
    STATUS_OK,
    STATUS_UNAVAILABLE,
)

# ==========================================================
# 1. Section Formatting Helpers
# ==========================================================


def _build_executive_summary(
    target_price_payload: dict[str, Any],
    sotp_payload: dict[str, Any],
) -> dict[str, Any]:
    """Formats Section 1: Executive Summary & Recommendation Card."""
    return {
        "symbol": target_price_payload.get("symbol"),
        "recommendation": target_price_payload.get("recommendation"),
        "recommendation_reason": target_price_payload.get("recommendation_reason"),
        "current_market_price": target_price_payload.get("market_price"),
        "target_price": target_price_payload.get("target_price"),
        "intrinsic_value_per_share": target_price_payload.get("intrinsic_value"),
        "upside_pct": target_price_payload.get("upside_pct"),
        "margin_of_safety_pct": target_price_payload.get("margin_of_safety_pct"),
        "valuation_gap": target_price_payload.get("valuation_gap"),
        "consolidated_equity_value": sotp_payload.get("equity_value"),
    }


def _build_valuation_summary(
    sotp_payload: dict[str, Any],
    target_price_payload: dict[str, Any],
) -> dict[str, Any]:
    """Formats Section 2: Concise Financial Overview Dashboard."""
    return {
        "enterprise_value": sotp_payload.get("enterprise_value"),
        "equity_value": sotp_payload.get("equity_value"),
        "intrinsic_value_per_share": sotp_payload.get("intrinsic_value_per_share"),
        "market_price": target_price_payload.get("market_price"),
        "target_price": target_price_payload.get("target_price"),
        "upside_pct": target_price_payload.get("upside_pct"),
        "recommendation": target_price_payload.get("recommendation"),
    }


def _build_sotp_breakdown_table(sotp_payload: dict[str, Any]) -> dict[str, Any]:
    """Formats Section 3: Consolidated SOTP Financial Bridge."""
    return {
        "gross_enterprise_value": sotp_payload.get("enterprise_value"),
        "total_cash": sotp_payload.get("cash"),
        "total_net_debt": sotp_payload.get("debt"),
        "total_minority_interest": sotp_payload.get("minority_interest"),
        "consolidated_equity_value": sotp_payload.get("equity_value"),
        "intrinsic_value_per_share": sotp_payload.get("intrinsic_value_per_share"),
        "shares_outstanding_millions": sotp_payload.get("shares_outstanding_millions"),
        "active_components_count": sotp_payload.get("component_count"),
        "component_breakdown": sotp_payload.get("component_breakdown", []),
    }


def _build_rich_portfolio_appendix(
    sotp_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    """Formats Section 5: Extended Entity-Level Portfolio Appendix."""
    breakdown = sotp_payload.get("component_breakdown", [])
    appendix = []
    for item in breakdown:
        appendix.append(
            {
                "entity": item.get("entity"),
                "interpretation": item.get("economic_interpretation", "OPERATING_ENTITY"),
                "classification": item.get("classification"),
                "classification_reason": item.get("classification_reason", "Rule matched"),
                "method": item.get("method"),
                "valuation_status": item.get("status"),
                "framework_complete": item.get("framework_complete", True),
                "model_complete": item.get("model_complete", False),
                "enterprise_value_mn": item.get("enterprise_value"),
                "equity_value_mn": item.get("equity_value"),
                "net_debt_mn": item.get("net_debt"),
                "value_contribution_mn": item.get("value_contribution"),
            }
        )
    return appendix


def _validate_report(report_payload: dict[str, Any]) -> bool:
    """Validates structural completeness of the research report."""
    if report_payload.get("status") != STATUS_OK:
        return False

    required_sections = [
        "executive_summary",
        "valuation_summary",
        "sotp_financial_bridge",
        "key_risks_and_assumptions",
        "portfolio_appendix",
    ]
    for section in required_sections:
        if section not in report_payload:
            return False

    exec_sum = report_payload["executive_summary"]
    if not exec_sum.get("recommendation") or exec_sum.get("target_price") is None:
        return False

    return True


def audit_report(
    symbol: str,
    rec: str,
    target_price: float,
    entities_count: int,
    error_count: int,
) -> None:
    """Prints standard Research Report Audit summary."""
    print("\n==========================================================")
    print("Equity Research Report Audit")
    print("==========================================================")
    print(f"Target Symbol        : {symbol}")
    print(f"Recommendation       : {rec}")
    print(f"Target Price         : ${target_price:,.2f}")
    print(f"Entities In Portfolio: {entities_count}")
    print(f"Report Errors        : {error_count}")
    print("==========================================================\n")


# ==========================================================
# 2. Main Service Function
# ==========================================================


def get_sotp_long_term_equity_report_service(
    symbol: str,
    override_market_price: float | None = None,
) -> dict[str, Any]:
    """
    Main Research Report Generation Service Routine.
    Gathers outputs across the pipeline and formats a professional research report.
    """
    # 1. Fetch Stage 15 Target Price payload
    target_price_payload = get_sotp_long_term_equity_target_price_service(
        symbol, override_market_price=override_market_price
    )
    if (
        not isinstance(target_price_payload, dict)
        or target_price_payload.get("status") != STATUS_OK
    ):
        return {
            "status": STATUS_UNAVAILABLE,
            "symbol": symbol,
            "message": "Target Price service unavailable or returned non-OK status.",
            "report_complete": False,
        }

    # 2. Fetch Stage 14 SOTP payload
    sotp_payload = get_sotp_long_term_equity_sotp_service(symbol)
    if not isinstance(sotp_payload, dict) or sotp_payload.get("status") != STATUS_OK:
        return {
            "status": STATUS_UNAVAILABLE,
            "symbol": symbol,
            "message": "SOTP Aggregation service unavailable or returned non-OK status.",
            "report_complete": False,
        }

    timestamp = get_current_timestamp()

    # 3. Assemble Metadata and Report Sections
    exec_summary = _build_executive_summary(target_price_payload, sotp_payload)
    val_summary = _build_valuation_summary(sotp_payload, target_price_payload)
    sotp_bridge = _build_sotp_breakdown_table(sotp_payload)
    appendix = _build_rich_portfolio_appendix(sotp_payload)

    # Resolve segment risks dynamically if segments exist; fallback to safe defensive default copy
    active_segments = sotp_payload.get("active_segments", [])
    resolved_risks = get_segment_risks(active_segments) if active_segments else get_default_risks()

    report_payload = {
        "status": STATUS_OK,
        "symbol": symbol,
        "report_title": f"Sum-of-the-Parts (SOTP) Equity Research Report: {symbol}",
        "metadata": {
            "report_version": PIPELINE_VERSION,
            "stage": STAGE_16,
            "generated_by": "AI Stock Analyzer Engine",
            "generated_at": timestamp,
        },
        "executive_summary": exec_summary,
        "valuation_summary": val_summary,
        "sotp_financial_bridge": sotp_bridge,
        "key_risks_and_assumptions": resolved_risks,
        "portfolio_appendix": appendix,
        "validation_error_count": 0,
        "report_complete": True,
    }

    # 4. Validate
    validation_error_count = 0
    if not _validate_report(report_payload):
        validation_error_count = 1
        report_payload["validation_error_count"] = validation_error_count
        report_payload["report_complete"] = False

    # 5. Audit Logging
    audit_report(
        symbol=symbol,
        rec=exec_summary["recommendation"],
        target_price=exec_summary["target_price"],
        entities_count=sotp_payload.get("total_records_processed", EXPECTED_ENTITY_COUNT),
        error_count=validation_error_count,
    )

    return report_payload


# ==========================================================
# 3. Self-Test Routine
# ==========================================================

if __name__ == "__main__":
    result = get_sotp_long_term_equity_report_service("RELIANCE")

    # Pipeline Verification Assertions
    assert result["status"] == STATUS_OK, f"Expected {STATUS_OK}, got {result['status']}"
    assert result["report_complete"] is True, "Report stage not marked complete"
    assert (
        result["validation_error_count"] == 0
    ), f"Expected 0 errors, got {result['validation_error_count']}"

    # Metadata Assertions
    assert "metadata" in result
    assert result["metadata"]["stage"] == STAGE_16
    assert result["metadata"]["report_version"] == PIPELINE_VERSION

    # Section Assertions
    assert "executive_summary" in result
    assert "valuation_summary" in result
    assert "sotp_financial_bridge" in result
    assert "key_risks_and_assumptions" in result
    assert "portfolio_appendix" in result
    assert isinstance(result["key_risks_and_assumptions"], list)
    assert len(result["key_risks_and_assumptions"]) > 0

    # Dashboard & Rich Appendix Check
    val_sum = result["valuation_summary"]
    assert "enterprise_value" in val_sum
    assert "target_price" in val_sum

    appendix_item = result["portfolio_appendix"][0]
    assert "interpretation" in appendix_item
    assert "classification_reason" in appendix_item
    assert "framework_complete" in appendix_item
    assert "model_complete" in appendix_item

    print("✅ Stage 16 Equity Research Report Service frozen, verified, and complete!")
