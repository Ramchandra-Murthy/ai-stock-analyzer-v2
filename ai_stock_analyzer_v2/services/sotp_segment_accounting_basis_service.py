from __future__ import annotations

from typing import Any


def get_sotp_segment_accounting_basis(symbol: str) -> dict[str, Any]:
    """
    Document the accounting basis of operating segment results
    used by the SOTP valuation engine.

    This is an evidence/control service only.
    It does not value associates or joint ventures and does not
    authorize any equity-bridge adjustment.
    """

    symbol = str(symbol or "").upper().strip()

    if symbol.endswith(".NS"):
        symbol = symbol[:-3]

    if symbol != "RELIANCE":
        return {
            "status": "UNAVAILABLE",
            "version": "V5.0",
            "symbol": symbol,
            "message": ("Segment accounting-basis evidence is not " "configured for this symbol."),
        }

    return {
        "status": "OK",
        "version": "V5.0",
        "symbol": symbol,
        "period": "FY2025-26",
        "currency": "INR",
        "unit": "crore",
        "segment_metric": "EBITDA",
        "associate_jv_treatment": "EXCLUDED_FROM_SEGMENT_RESULTS",
        "evidence": {
            "segment_results_reported_separately": True,
            "associate_jv_profit_reported_separately": True,
            "profit_before_associate_jv_share": 123162.0,
            "associate_jv_share_of_profit": 144.0,
        },
        "operating_overlap_implication": {
            "accounting_overlap_cleared": True,
            "meaning": (
                "Equity-accounted share of profit or loss from "
                "associates and joint ventures is reported outside "
                "the segment-result reconciliation."
            ),
        },
        "bridge_ready": False,
        "interpretation": (
            "FY2025-26 consolidated reporting presents the share "
            "of profit or loss of associates and joint ventures "
            "separately from the segment-result reconciliation. "
            "This supports treating equity-accounted associate/JV "
            "earnings as excluded from the operating segment "
            "results used by the SOTP engine. This accounting "
            "conclusion does not establish entity-level economic "
            "independence or fair value."
        ),
        "warnings": [
            (
                "Exclusion of equity-accounted earnings from segment "
                "results does not automatically make every associate "
                "or JV an incremental SOTP asset."
            ),
            (
                "Entity-level ownership, economic overlap and "
                "valuation basis must still be established."
            ),
            ("Accounting carrying values must not automatically " "be used as SOTP fair values."),
        ],
    }
