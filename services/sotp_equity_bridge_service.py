from __future__ import annotations

from typing import Any

from services.research_service import get_stock_profile
from services.sotp_adjustment_service import (
    build_sotp_adjustments,
)
from services.sotp_new_energy_scenario_policy_service import (
    authorize_sotp_new_energy_scenarios,
)
from services.sotp_segment_valuation_service import (
    generate_operating_sotp_valuation,
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


def _round(value, digits=2):
    value = _num(value)

    if value is None:
        return None

    return round(value, digits)


def _crore_to_rupees(value: float) -> float:
    return value * 1e7


def generate_sotp_equity_bridge(
    symbol: str,
) -> dict[str, Any]:

    symbol = symbol.upper().replace(".NS", "").strip()

    # ======================================================
    # 1. OPERATING ENTERPRISE VALUE
    # ======================================================

    operating = generate_operating_sotp_valuation(symbol)

    if not isinstance(operating, dict) or operating.get("status") != "OK":
        return {
            "status": "ERROR",
            "version": "V5.0",
            "symbol": symbol,
            "message": "Operating SOTP valuation unavailable.",
            "operating": operating,
        }

    operating_ev = _num(operating.get("operating_enterprise_value"))

    if operating_ev is None:
        return {
            "status": "ERROR",
            "version": "V5.0",
            "symbol": symbol,
            "message": "Operating enterprise value unavailable.",
            "operating": operating,
        }

    # ======================================================
    # 2. NEW ENERGY SCENARIO VALUES
    # ======================================================

    new_energy = authorize_sotp_new_energy_scenarios(symbol)

    scenario_range_authorized = False
    scenario_values = {}

    if (
        isinstance(new_energy, dict)
        and new_energy.get("status") == "OK"
        and new_energy.get("scenario_range_authorized") is True
    ):
        raw_scenarios = new_energy.get(
            "authorized_scenario_values",
            {},
        )

        if isinstance(raw_scenarios, dict):

            for scenario in ("BEAR", "BASE", "BULL"):

                value = _num(raw_scenarios.get(scenario))

                if value is not None:
                    scenario_values[scenario] = value

        scenario_range_authorized = all(
            scenario in scenario_values for scenario in ("BEAR", "BASE", "BULL")
        )

    # ======================================================
    # 3. CENTRALIZED EQUITY-BRIDGE ADJUSTMENTS
    # ======================================================

    adjustments = build_sotp_adjustments(symbol)

    if not isinstance(adjustments, dict) or adjustments.get("status") != "OK":
        return {
            "status": "ERROR",
            "version": "V5.0",
            "symbol": symbol,
            "message": "SOTP adjustment engine unavailable.",
            "operating": operating,
            "new_energy": new_energy,
            "adjustments": adjustments,
        }

    bridge = adjustments.get(
        "equity_bridge",
        {},
    )

    bridge_adjustment = _num(bridge.get("final_equity_bridge_adjustment"))

    if bridge_adjustment is None:
        return {
            "status": "ERROR",
            "version": "V5.0",
            "symbol": symbol,
            "message": ("Authorized equity bridge adjustment " "is unavailable."),
            "operating": operating,
            "new_energy": new_energy,
            "adjustments": adjustments,
        }

    # ======================================================
    # 4. SHARES AND CURRENT PRICE
    # ======================================================

    profile = get_stock_profile(symbol) or {}

    shares = _num(profile.get("shares_outstanding"))

    current_price = _num(profile.get("price"))

    # ======================================================
    # 5. BUILD BEAR / BASE / BULL SOTP
    # ======================================================

    scenarios = {}

    if scenario_range_authorized:

        for scenario in ("BEAR", "BASE", "BULL"):

            new_energy_ev = scenario_values[scenario]

            gross_enterprise_value = operating_ev + new_energy_ev

            equity_value = gross_enterprise_value + bridge_adjustment

            fair_value_per_share = None
            upside_percent = None

            if shares is not None and shares > 0:

                fair_value_per_share = _crore_to_rupees(equity_value) / shares

            if fair_value_per_share is not None and current_price is not None and current_price > 0:

                upside_percent = (fair_value_per_share / current_price - 1) * 100

            scenarios[scenario] = {
                "operating_enterprise_value": (_round(operating_ev)),
                "new_energy_enterprise_value": (_round(new_energy_ev)),
                "gross_enterprise_value": (_round(gross_enterprise_value)),
                "equity_bridge_adjustment": (_round(bridge_adjustment)),
                "equity_value": (_round(equity_value)),
                "fair_value_per_share": (_round(fair_value_per_share)),
                "upside_percent": (_round(upside_percent)),
            }

    # ======================================================
    # 6. PENDING ITEMS
    # ======================================================

    pending_items = bridge.get(
        "pending_items",
        [],
    )

    if not isinstance(pending_items, list):
        pending_items = []

    pending_exposure = _num(bridge.get("pending_exposure"))

    pending_item_count = bridge.get(
        "pending_item_count",
        len(pending_items),
    )

    bridge_status = bridge.get("status")

    # ======================================================
    # 7. VALUATION STATUS
    # ======================================================

    if not scenario_range_authorized:

        valuation_status = "NEW_ENERGY_SCENARIOS_UNAVAILABLE"

    elif bridge_status == "FINAL":

        valuation_status = "FINAL"

    else:

        valuation_status = "PROVISIONAL"

    # ======================================================
    # 8. CONFIDENCE
    # ======================================================

    operating_coverage = _num(operating.get("operating_coverage")) or 0.0

    operating_reliability = _num(operating.get("weighted_reliability")) or 0.0

    confidence_score = operating_coverage * operating_reliability * 100.0

    if valuation_status != "FINAL":
        confidence_score *= 0.75

    confidence_score = round(
        confidence_score,
        2,
    )

    if confidence_score >= 80:
        confidence = "HIGH"

    elif confidence_score >= 60:
        confidence = "MODERATE"

    else:
        confidence = "LOW"

    # ======================================================
    # OUTPUT
    # ======================================================

    return {
        "status": "OK",
        "version": "V5.0",
        "symbol": symbol,
        "currency": operating.get(
            "currency",
            "INR",
        ),
        "unit": operating.get(
            "unit",
            "crore",
        ),
        "period": operating.get("period"),
        "operating_enterprise_value": (_round(operating_ev)),
        "new_energy": {
            "scenario_range_authorized": (scenario_range_authorized),
            "scenario_values": {key: _round(value) for key, value in scenario_values.items()},
            "treatment": ("INCLUDE_IN_GROSS_SOTP_EV"),
        },
        "equity_bridge": {
            "authorized_adjustment": (_round(bridge_adjustment)),
            "status": bridge_status,
            "pending_exposure": (_round(pending_exposure)),
            "pending_item_count": (pending_item_count),
            "pending_items": pending_items,
        },
        "shares_outstanding": shares,
        "current_price": current_price,
        "scenarios": scenarios,
        "valuation_status": (valuation_status),
        "confidence": confidence,
        "confidence_score": (confidence_score),
        "interpretation": (
            "Operating enterprise value is combined "
            "with the authorized New Energy Bear, Base "
            "and Bull scenario values. The centralized "
            "SOTP adjustment engine then converts gross "
            "enterprise value into scenario equity "
            "values. Unresolved investment and ownership "
            "items remain excluded until explicitly "
            "authorized."
        ),
        "warnings": [
            (
                "New Energy scenario values are "
                "model-derived and are not reported "
                "enterprise values."
            ),
            ("A PROVISIONAL valuation must not be " "presented as a completed SOTP fair " "value."),
            ("Pending positive assets may increase " "equity value when authorized."),
            (
                "Pending ownership or debt-like claims "
                "may reduce equity value when "
                "authorized."
            ),
        ],
        "components": {
            "operating": operating,
            "new_energy_policy": new_energy,
            "adjustments": adjustments,
        },
    }
