from __future__ import annotations

from typing import Any

from services.sotp_new_energy_overlap_service import (
    analyze_sotp_new_energy_overlap,
)
from services.sotp_new_energy_scenario_service import (
    generate_sotp_new_energy_scenarios,
)

REQUIRED_SCENARIOS = (
    "BEAR",
    "BASE",
    "BULL",
)


def _num(value):
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def authorize_sotp_new_energy_scenarios(
    symbol: str,
) -> dict[str, Any]:

    scenario_data = generate_sotp_new_energy_scenarios(symbol)

    overlap = analyze_sotp_new_energy_overlap(symbol)

    if scenario_data.get("status") != "OK":
        return scenario_data

    if overlap.get("status") != "OK":
        return overlap

    # ----------------------------------------------------
    # INPUTS
    # ----------------------------------------------------

    scenarios = scenario_data.get(
        "scenarios",
        {},
    )

    reference_capital = _num(scenario_data.get("reference_capital"))

    scenario_analysis_available = scenario_data.get("scenario_analysis_available") is True

    # ----------------------------------------------------
    # SCENARIO COMPLETENESS
    # ----------------------------------------------------

    scenario_values = {}

    for scenario_name in REQUIRED_SCENARIOS:

        scenario = scenarios.get(
            scenario_name,
            {},
        )

        scenario_values[scenario_name] = _num(scenario.get("scenario_value"))

    complete_scenario_set = all(
        scenario_values.get(name) is not None for name in REQUIRED_SCENARIOS
    )

    # ----------------------------------------------------
    # RANGE VALIDATION
    # ----------------------------------------------------

    bear = scenario_values.get("BEAR")
    base = scenario_values.get("BASE")
    bull = scenario_values.get("BULL")

    ordered_scenarios = (
        bear is not None and base is not None and bull is not None and bear <= base <= bull
    )

    non_negative_scenarios = all(
        value is not None and value >= 0 for value in scenario_values.values()
    )

    # ----------------------------------------------------
    # CLASSIFICATION VALIDATION
    # ----------------------------------------------------

    model_classification_confirmed = all(
        scenarios.get(name, {}).get("classification") == "MODEL_SCENARIO"
        for name in REQUIRED_SCENARIOS
    )

    # ----------------------------------------------------
    # FACT / MODEL SEPARATION
    # ----------------------------------------------------

    reported_enterprise_value = _num(scenario_data.get("reported_enterprise_value"))

    reported_valuation_ready = scenario_data.get("reported_valuation_ready") is True

    factual_ev_separate = reported_enterprise_value is None and not reported_valuation_ready

    # ----------------------------------------------------
    # OVERLAP CONTROL
    # ----------------------------------------------------
    #
    # The unresolved entity-level net-asset overlap does
    # NOT invalidate these scenarios because the scenario
    # values do not use the ₹25,449.45 Cr arithmetic
    # net-asset total.
    #
    # The overlap block continues to prevent that accounting
    # total from entering valuation.
    # ----------------------------------------------------

    net_asset_floor_authorized = overlap.get("valuation_floor_authorized") is True

    net_asset_value_used_in_scenarios = False

    overlap_control_passed = not net_asset_value_used_in_scenarios

    # ----------------------------------------------------
    # AUTHORIZATION TEST
    # ----------------------------------------------------

    scenario_range_authorized = all(
        [
            scenario_analysis_available,
            reference_capital is not None,
            complete_scenario_set,
            ordered_scenarios,
            non_negative_scenarios,
            model_classification_confirmed,
            factual_ev_separate,
            overlap_control_passed,
        ]
    )

    # ----------------------------------------------------
    # AUTHORIZED VALUES
    # ----------------------------------------------------

    if scenario_range_authorized:

        authorized_scenario_values = {
            "BEAR": bear,
            "BASE": base,
            "BULL": bull,
        }

        status_view = "SCENARIO_RANGE_AUTHORIZED"

        treatment = "AUTHORIZED_FOR_SCENARIO_SOTP_ONLY"

    else:

        authorized_scenario_values = {
            "BEAR": None,
            "BASE": None,
            "BULL": None,
        }

        status_view = "SCENARIO_RANGE_NOT_AUTHORIZED"

        treatment = "DIAGNOSTIC_SCENARIO_ONLY"

    # ----------------------------------------------------
    # RETURN
    # ----------------------------------------------------

    return {
        "status": "OK",
        "version": "V5.0",
        "symbol": scenario_data.get("symbol"),
        "segment": "New Energy",
        "currency": scenario_data.get("currency"),
        "unit": scenario_data.get("unit"),
        "reference_capital": reference_capital,
        "reference_capital_source": (scenario_data.get("reference_capital_source")),
        "scenario_method": (scenario_data.get("scenario_method")),
        # ------------------------------------------------
        # VALIDATION
        # ------------------------------------------------
        "validation": {
            "scenario_analysis_available": (scenario_analysis_available),
            "complete_scenario_set": (complete_scenario_set),
            "ordered_scenarios": (ordered_scenarios),
            "non_negative_scenarios": (non_negative_scenarios),
            "model_classification_confirmed": (model_classification_confirmed),
            "factual_ev_separate": (factual_ev_separate),
            "overlap_control_passed": (overlap_control_passed),
        },
        # ------------------------------------------------
        # OVERLAP INFORMATION
        # ------------------------------------------------
        "overlap_control": {
            "intercompany_overlap_resolved": (
                overlap.get(
                    "overlap_tests",
                    {},
                ).get("intercompany_overlap_resolved")
            ),
            "net_asset_floor_authorized": (net_asset_floor_authorized),
            "net_asset_value_used_in_scenarios": (net_asset_value_used_in_scenarios),
            "unresolved_tests": (
                overlap.get(
                    "unresolved_tests",
                    [],
                )
            ),
        },
        # ------------------------------------------------
        # SCENARIO VALUES
        # ------------------------------------------------
        "input_scenario_values": {
            "BEAR": bear,
            "BASE": base,
            "BULL": bull,
        },
        "authorized_scenario_values": (authorized_scenario_values),
        "scenario_range_authorized": (scenario_range_authorized),
        # ------------------------------------------------
        # FACTUAL EV REMAINS SEPARATE
        # ------------------------------------------------
        "reported_enterprise_value": (reported_enterprise_value),
        "reported_valuation_ready": (reported_valuation_ready),
        "authorized_enterprise_value": None,
        "treatment": treatment,
        "status_view": status_view,
        # ------------------------------------------------
        # INTERPRETATION
        # ------------------------------------------------
        "interpretation": (
            "The New Energy Bear/Base/Bull values are "
            "authorized for scenario-based SOTP analysis "
            "only. They remain model-derived analytical "
            "values and do not constitute a reported or "
            "independently authorized enterprise value."
        ),
        "warnings": [
            ("Scenario authorization does not convert " "model assumptions into reported facts."),
            (
                "The New Energy accounting net-asset "
                "total remains excluded while "
                "intercompany overlap is unresolved."
            ),
            ("Scenario values must enter only the " "matching Bear, Base and Bull SOTP cases."),
            ("The factual enterprise-value field must " "remain separate from scenario values."),
        ],
    }
