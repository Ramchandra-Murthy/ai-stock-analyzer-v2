from __future__ import annotations

from typing import Any

from services.sotp_equity_bridge_service import (
    generate_sotp_equity_bridge,
)


def _num(value: Any):
    if isinstance(value, (int, float)):
        try:
            if value != value:
                return None
        except Exception:
            pass
        return float(value)
    return None


def analyze_sotp_completeness(
    symbol: str,
) -> dict[str, Any]:

    symbol = symbol.upper().strip()

    bridge = generate_sotp_equity_bridge(symbol)

    if bridge.get("status") != "OK":
        return {
            "status": "ERROR",
            "symbol": symbol,
            "message": "SOTP equity bridge unavailable.",
            "bridge": bridge,
        }

    components = bridge.get("components", {})

    operating = components.get("operating", {})

    segments = operating.get("segments", {})

    if not isinstance(segments, dict):
        segments = {}

    # -----------------------------------------
    # SEGMENT COMPLETENESS
    # -----------------------------------------

    segment_results = {}

    total_segment_count = len(segments)
    valued_segment_count = 0
    pending_segment_count = 0

    for key, item in segments.items():

        if not isinstance(item, dict):
            continue

        status = item.get("status")

        valued = status == "OK" and _num(item.get("enterprise_value")) is not None

        if valued:
            valued_segment_count += 1
        else:
            pending_segment_count += 1

        segment_results[key] = {
            "status": status,
            "valued": valued,
            "method": item.get("method"),
            "enterprise_value": _num(item.get("enterprise_value")),
            "message": item.get("message"),
        }

    segment_completion_ratio = (
        valued_segment_count / total_segment_count if total_segment_count > 0 else 0.0
    )

    # -----------------------------------------
    # BRIDGE COMPLETENESS
    # -----------------------------------------

    pending_bridge_items = bridge.get(
        "pending_items",
        [],
    )

    if not isinstance(pending_bridge_items, list):
        pending_bridge_items = []

    pending_bridge_count = len(pending_bridge_items)

    bridge_complete = bridge.get("bridge_complete") is True

    # -----------------------------------------
    # UNRESOLVED ECONOMIC ITEMS
    # -----------------------------------------

    unresolved_items = []

    for key, item in segment_results.items():

        if item["valued"]:
            continue

        unresolved_items.append(
            {
                "key": key,
                "category": "SEGMENT",
                "status": item["status"],
                "method": item["method"],
                "value": None,
                "message": item["message"],
            }
        )

    for item in pending_bridge_items:

        if not isinstance(item, dict):
            continue

        unresolved_items.append(
            {
                "key": item.get("key"),
                "category": item.get("category"),
                "status": "PENDING",
                "method": item.get("treatment"),
                "value": _num(item.get("value")),
                "message": item.get("reason"),
            }
        )

    unresolved_count = len(unresolved_items)

    # -----------------------------------------
    # STATUS
    # -----------------------------------------

    economic_complete = pending_segment_count == 0 and bridge_complete

    if economic_complete:
        completeness_status = "COMPLETE"

    elif valued_segment_count > 0 and bridge.get("authorized_equity_value") is not None:
        completeness_status = "PARTIAL"

    else:
        completeness_status = "INSUFFICIENT"

    # -----------------------------------------
    # OUTPUT
    # -----------------------------------------

    return {
        "status": "OK",
        "version": "V5.0",
        "symbol": symbol,
        "operating_coverage_percent": (operating.get("operating_coverage_percent")),
        "economic_segment_coverage": {
            "total_segments": total_segment_count,
            "valued_segments": valued_segment_count,
            "pending_segments": pending_segment_count,
            "completion_ratio": round(
                segment_completion_ratio,
                4,
            ),
            "completion_percent": round(
                segment_completion_ratio * 100,
                1,
            ),
        },
        "segments": segment_results,
        "equity_bridge": {
            "bridge_complete": bridge_complete,
            "pending_bridge_items": (pending_bridge_count),
        },
        "unresolved_item_count": (unresolved_count),
        "unresolved_items": unresolved_items,
        "economic_complete": economic_complete,
        "completeness_status": (completeness_status),
        "valuation_status": (bridge.get("valuation_status")),
        "provisional_fair_value_per_share": (bridge.get("fair_value_per_share")),
        "interpretation": (
            "Operating coverage measures completion "
            "of the multiple-valued operating segments. "
            "Economic completeness additionally requires "
            "all SOTP segments and equity-bridge items "
            "to be resolved."
        ),
    }
