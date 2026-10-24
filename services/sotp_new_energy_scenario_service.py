from __future__ import annotations

from typing import Any

from services.sotp_new_energy_data_service import (
    get_sotp_new_energy_data,
)
from services.sotp_new_energy_valuation_service import (
    value_sotp_new_energy,
)

# ============================================================
# NEW ENERGY SCENARIO ASSUMPTIONS
# ============================================================
#
# IMPORTANT:
#
# These are MODEL ASSUMPTIONS.
# They are NOT reported company facts.
#
# Investment commitment is used only as a reference capital
# base for scenario analysis. It is NOT treated directly as EV.
#
# ============================================================

SCENARIO_ASSUMPTIONS = {
    "BEAR": {
        "capital_realization_factor": 0.40,
        "strategic_multiple": 0.80,
    },
    "BASE": {
        "capital_realization_factor": 0.60,
        "strategic_multiple": 1.00,
    },
    "BULL": {
        "capital_realization_factor": 0.80,
        "strategic_multiple": 1.25,
    },
}


def _num(value):
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def generate_sotp_new_energy_scenarios(
    symbol: str,
) -> dict[str, Any]:

    data = get_sotp_new_energy_data(symbol)

    valuation = value_sotp_new_energy(symbol)

    if data.get("status") != "OK":
        return data

    investment = data.get("investment", {})

    committed_investment = _num(investment.get("committed_investment"))

    announced_investment = _num(investment.get("announced_investment"))

    reference_capital = (
        committed_investment if committed_investment is not None else announced_investment
    )

    # --------------------------------------------------------
    # SCENARIO ENGINE
    # --------------------------------------------------------

    scenarios = {}

    if reference_capital is not None:

        for scenario_name, assumptions in SCENARIO_ASSUMPTIONS.items():

            realization_factor = assumptions["capital_realization_factor"]

            strategic_multiple = assumptions["strategic_multiple"]

            realized_capital = reference_capital * realization_factor

            scenario_value = realized_capital * strategic_multiple

            scenarios[scenario_name] = {
                "reference_capital": round(
                    reference_capital,
                    2,
                ),
                "capital_realization_factor": (realization_factor),
                "realized_capital": round(
                    realized_capital,
                    2,
                ),
                "strategic_multiple": (strategic_multiple),
                "scenario_value": round(
                    scenario_value,
                    2,
                ),
                "classification": ("MODEL_SCENARIO"),
                "authorized_for_sotp": False,
            }

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    scenario_values = {name: scenario.get("scenario_value") for name, scenario in scenarios.items()}

    return {
        "status": "OK",
        "version": "V5.0",
        "symbol": data.get("symbol"),
        "segment": "New Energy",
        "currency": data.get("currency"),
        "unit": data.get("unit"),
        "reference_capital": reference_capital,
        "reference_capital_source": (
            "committed_investment" if committed_investment is not None else "announced_investment"
        ),
        "scenario_method": ("CAPITAL_REALIZATION_X_STRATEGIC_MULTIPLE"),
        "scenarios": scenarios,
        "scenario_values": scenario_values,
        "reported_enterprise_value": (valuation.get("enterprise_value")),
        "reported_valuation_ready": (valuation.get("valuation_ready")),
        "scenario_analysis_available": (len(scenarios) > 0),
        "authorized_for_sotp": False,
        "status_view": (
            "SCENARIO_ANALYSIS_AVAILABLE_" "NOT_AUTHORIZED_FOR_SOTP"
            if scenarios
            else "SCENARIO_INPUT_UNAVAILABLE"
        ),
        "interpretation": (
            "New Energy scenario values are model-derived "
            "analytical estimates. They are not reported "
            "enterprise values and are not automatically "
            "authorized for the SOTP bridge."
        ),
        "warnings": [
            ("The investment commitment is used only " "as a scenario reference capital base."),
            (
                "Scenario realization factors and "
                "strategic multiples are analyst "
                "assumptions, not company disclosures."
            ),
            ("Scenario values must remain separate " "from authorized enterprise value."),
        ],
    }
