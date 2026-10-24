from __future__ import annotations

from typing import Any

from services.sotp_valuation_service import generate_sotp_valuation

TOLERANCE = 1.0


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


def _close(a, b, tolerance=TOLERANCE):
    a = _num(a)
    b = _num(b)

    if a is None or b is None:
        return False

    return abs(a - b) <= tolerance


def validate_sotp_valuation(
    symbol: str,
) -> dict[str, Any]:

    symbol = symbol.upper().strip()

    valuation = generate_sotp_valuation(symbol)

    if valuation.get("status") != "OK":
        return {
            "status": "ERROR",
            "symbol": symbol,
            "message": "SOTP valuation unavailable.",
            "valuation": valuation,
        }

    failures: list[str] = []
    warnings: list[str] = []

    # --------------------------------------------------
    # 1. OPERATING SEGMENT ARITHMETIC
    # --------------------------------------------------

    segments = valuation.get("segments", {})

    operating_keys = [
        "o2c",
        "digital",
        "retail",
        "upstream",
    ]

    calculated_operating_ev = 0.0
    operating_values_available = True

    for key in operating_keys:

        block = segments.get(key, {})

        ev = _num(block.get("enterprise_value"))

        if ev is None:
            operating_values_available = False
            failures.append(f"OPERATING_SEGMENT_VALUE_MISSING:{key}")
            continue

        calculated_operating_ev += ev

    reported_operating_ev = _num(valuation.get("operating_enterprise_value"))

    operating_ev_reconciles = operating_values_available and _close(
        calculated_operating_ev,
        reported_operating_ev,
    )

    if not operating_ev_reconciles:
        failures.append("OPERATING_EV_RECONCILIATION_FAILED")

    # --------------------------------------------------
    # 2. SCENARIO ARITHMETIC
    # --------------------------------------------------

    scenarios = valuation.get("scenarios", {})

    scenario_results = {}

    for scenario_name in ["BEAR", "BASE", "BULL"]:

        scenario = scenarios.get(scenario_name, {})

        operating_ev = _num(scenario.get("operating_enterprise_value"))

        new_energy_ev = _num(scenario.get("new_energy_enterprise_value"))

        gross_ev = _num(scenario.get("gross_enterprise_value"))

        bridge_adjustment = _num(scenario.get("equity_bridge_adjustment"))

        equity_value = _num(scenario.get("equity_value"))

        expected_gross_ev = None
        expected_equity_value = None

        gross_reconciles = False
        equity_reconciles = False

        if operating_ev is not None and new_energy_ev is not None:
            expected_gross_ev = operating_ev + new_energy_ev

            gross_reconciles = _close(
                expected_gross_ev,
                gross_ev,
            )

        if gross_ev is not None and bridge_adjustment is not None:
            expected_equity_value = gross_ev + bridge_adjustment

            equity_reconciles = _close(
                expected_equity_value,
                equity_value,
            )

        if not gross_reconciles:
            failures.append(f"{scenario_name}_GROSS_EV_RECONCILIATION_FAILED")

        if not equity_reconciles:
            failures.append(f"{scenario_name}_EQUITY_VALUE_RECONCILIATION_FAILED")

        scenario_results[scenario_name] = {
            "expected_gross_enterprise_value": (
                round(expected_gross_ev, 2) if expected_gross_ev is not None else None
            ),
            "reported_gross_enterprise_value": gross_ev,
            "gross_ev_reconciles": gross_reconciles,
            "expected_equity_value": (
                round(expected_equity_value, 2) if expected_equity_value is not None else None
            ),
            "reported_equity_value": equity_value,
            "equity_value_reconciles": equity_reconciles,
        }

    # --------------------------------------------------
    # 3. BASE / HEADLINE CONSISTENCY
    # --------------------------------------------------

    base = scenarios.get("BASE", {})

    headline_gross_ev = _num(valuation.get("gross_enterprise_value"))

    headline_equity_value = _num(valuation.get("equity_value"))

    headline_fair_value = _num(valuation.get("fair_value_per_share"))

    base_matches_headline = all(
        [
            _close(
                headline_gross_ev,
                base.get("gross_enterprise_value"),
            ),
            _close(
                headline_equity_value,
                base.get("equity_value"),
            ),
            _close(
                headline_fair_value,
                base.get("fair_value_per_share"),
                tolerance=0.01,
            ),
        ]
    )

    if not base_matches_headline:
        failures.append("BASE_HEADLINE_MISMATCH")

    # --------------------------------------------------
    # 4. PER-SHARE ARITHMETIC
    # --------------------------------------------------

    shares = _num(valuation.get("shares_outstanding"))

    calculated_fair_value = None

    per_share_reconciles = False

    if shares is not None and shares > 0 and headline_equity_value is not None:
        calculated_fair_value = headline_equity_value * 1e7 / shares

        per_share_reconciles = _close(
            calculated_fair_value,
            headline_fair_value,
            tolerance=0.02,
        )

    if not per_share_reconciles:
        failures.append("PER_SHARE_RECONCILIATION_FAILED")

    # --------------------------------------------------
    # 5. SCENARIO ORDERING
    # --------------------------------------------------

    bear_value = _num(scenarios.get("BEAR", {}).get("new_energy_enterprise_value"))

    base_value = _num(scenarios.get("BASE", {}).get("new_energy_enterprise_value"))

    bull_value = _num(scenarios.get("BULL", {}).get("new_energy_enterprise_value"))

    scenario_order_valid = (
        bear_value is not None
        and base_value is not None
        and bull_value is not None
        and bear_value <= base_value <= bull_value
    )

    if not scenario_order_valid:
        failures.append("NEW_ENERGY_SCENARIO_ORDER_INVALID")

    # --------------------------------------------------
    # 6. NEW ENERGY DOUBLE-COUNTING CONTROL
    # --------------------------------------------------

    components = valuation.get("components", {})

    adjustments = components.get("adjustments", {})

    new_energy_control = adjustments.get(
        "new_energy",
        {},
    )

    new_energy_bridge_treatment = new_energy_control.get("equity_bridge_treatment")

    new_energy_double_count_control = (
        new_energy_bridge_treatment == "EXCLUDED_FROM_BRIDGE_INCLUDE_IN_GROSS_SOTP_EV"
    )

    if not new_energy_double_count_control:
        failures.append("NEW_ENERGY_DOUBLE_COUNT_CONTROL_FAILED")

    # --------------------------------------------------
    # 7. PENDING ASSET CONTROL
    # --------------------------------------------------

    equity_bridge = adjustments.get(
        "equity_bridge",
        {},
    )

    authorized_adjustments = equity_bridge.get(
        "authorized_adjustments",
        {},
    )

    pending_asset_controls = {}

    for key in [
        "short_term_investments",
        "financial_investments",
        "long_term_equity_investment",
        "minority_interest",
    ]:

        value = _num(authorized_adjustments.get(key))

        excluded = value is not None and abs(value) <= TOLERANCE

        pending_asset_controls[key] = excluded

        if not excluded:
            failures.append(f"PENDING_ITEM_ENTERED_BRIDGE:{key}")

    # --------------------------------------------------
    # 8. RETAIL MULTIPLE CAP DIAGNOSTIC
    # --------------------------------------------------

    retail = segments.get("retail", {})

    retail_multiple = _num(retail.get("valuation_multiple"))

    retail_cap_respected = retail_multiple is not None and retail_multiple <= 30.0

    if not retail_cap_respected:
        failures.append("RETAIL_MULTIPLE_CAP_FAILED")

    if retail_multiple is not None and retail_multiple >= 30.0:
        warnings.append("Retail valuation is operating at the 30x " "EV/EBITDA policy cap.")

    # --------------------------------------------------
    # 9. STATUS INTEGRITY
    # --------------------------------------------------

    pending_count = valuation.get(
        "pending_item_count",
        0,
    )

    valuation_status = valuation.get("valuation_status")

    status_consistent = not (pending_count > 0 and valuation_status == "FINAL")

    if not status_consistent:
        failures.append("FINAL_STATUS_WITH_PENDING_ITEMS")

    # --------------------------------------------------
    # FINAL VALIDATION VIEW
    # --------------------------------------------------

    validation_passed = len(failures) == 0

    if validation_passed and warnings:
        validation_status = "PASS_WITH_WARNINGS"
    elif validation_passed:
        validation_status = "PASS"
    else:
        validation_status = "FAIL"

    return {
        "status": "OK",
        "version": "V5.0",
        "symbol": symbol,
        "validation_status": validation_status,
        "validation_passed": validation_passed,
        "checks": {
            "operating_ev_reconciles": (operating_ev_reconciles),
            "scenario_arithmetic": scenario_results,
            "base_matches_headline": (base_matches_headline),
            "per_share_reconciles": (per_share_reconciles),
            "scenario_order_valid": (scenario_order_valid),
            "new_energy_double_count_control": (new_energy_double_count_control),
            "pending_asset_controls": (pending_asset_controls),
            "retail_multiple_cap_respected": (retail_cap_respected),
            "status_consistent": (status_consistent),
        },
        "reconciliation": {
            "calculated_operating_enterprise_value": (round(calculated_operating_ev, 2)),
            "reported_operating_enterprise_value": (reported_operating_ev),
            "calculated_fair_value_per_share": (
                round(calculated_fair_value, 2) if calculated_fair_value is not None else None
            ),
            "reported_fair_value_per_share": (headline_fair_value),
        },
        "failure_count": len(failures),
        "failures": failures,
        "warning_count": len(warnings),
        "warnings": warnings,
        "valuation_status": valuation_status,
        "pending_item_count": pending_count,
        "interpretation": (
            "This service independently validates SOTP "
            "arithmetic, scenario consistency, bridge "
            "authorization controls, per-share valuation, "
            "scenario ordering and selected valuation "
            "policy constraints."
        ),
    }
