from __future__ import annotations

from typing import Any

# ============================================================
# SOTP V5.0 — NEW ENERGY FACTUAL DATA
# ============================================================
#
# IMPORTANT:
# This service stores reported / source-supported facts.
#
# It does NOT:
#   - value New Energy,
#   - convert investment commitment into enterprise value,
#   - assume planned capacity is commissioned,
#   - assign valuation multiples.
#
# Valuation belongs in a separate valuation service.
# ============================================================


NEW_ENERGY_DATA = {
    "RELIANCE": {
        "currency": "INR",
        "unit": "crore",
        "segment": "New Energy",
        "valuation_method": "STRATEGIC_VALUE",
        # ----------------------------------------------------
        # CAPITAL / INVESTMENT
        # ----------------------------------------------------
        #
        # ₹75,000 Cr represents Reliance's disclosed
        # clean-energy investment commitment.
        #
        # It is NOT treated here as:
        #   - capital deployed,
        #   - capital employed,
        #   - enterprise value.
        # ----------------------------------------------------
        "investment": {
            "announced_investment": 75000.0,
            "committed_investment": 75000.0,
            # Actual cumulative capital deployed has not
            # been established from the evidence used here.
            "capital_deployed": None,
            # New Energy-specific capital employed has not
            # been established.
            "capital_employed": None,
            "source": ("Reliance Industries Integrated Annual Report " "FY2025-26"),
            "source_period": "FY2025-26",
            "reliability": 0.95,
        },
        # ----------------------------------------------------
        # SOLAR PV MANUFACTURING
        # ----------------------------------------------------
        "solar": {
            # Long-term planned manufacturing expansion.
            "planned_capacity_gw": 20.0,
            # Phase / ramp capacity toward which operations
            # are scaling.
            "under_construction_capacity_gw": 10.0,
            # Do NOT treat 200 MWp module production as
            # 0.2 GW of installed annual manufacturing
            # capacity. It is recorded separately below.
            "commissioned_capacity_gw": None,
            "production_capacity_gw": None,
            # Reported first HJT module production.
            "reported_initial_production_mwp": 200.0,
            "status": "RAMPING",
            "source": ("Reliance Industries Integrated Annual Report " "FY2025-26"),
            "reliability": 0.95,
        },
        # ----------------------------------------------------
        # BATTERY / ENERGY STORAGE
        # ----------------------------------------------------
        "battery": {
            # Long-term scalable capacity.
            "planned_capacity_gwh": 100.0,
            # Initial manufacturing capacity under
            # commissioning / ramp.
            "under_construction_capacity_gwh": 40.0,
            "commissioned_capacity_gwh": None,
            "production_capacity_gwh": None,
            "status": "ADVANCED_COMMISSIONING",
            "source": ("Reliance Industries Integrated Annual Report " "FY2025-26"),
            "reliability": 0.95,
        },
        # ----------------------------------------------------
        # ELECTROLYSER MANUFACTURING
        # ----------------------------------------------------
        "electrolyser": {
            # Manufacturing capacity scalable to 3 GW/year.
            "planned_capacity_gw": 3.0,
            "under_construction_capacity_gw": None,
            "commissioned_capacity_gw": None,
            "production_capacity_gw": None,
            "status": "UNDER_DEVELOPMENT",
            "source": ("Reliance Industries Integrated Annual Report " "FY2025-26"),
            "reliability": 0.95,
        },
        # ----------------------------------------------------
        # GREEN HYDROGEN
        # ----------------------------------------------------
        "green_hydrogen": {
            # Strategic target rather than current production.
            "planned_capacity": 3.0,
            "under_construction_capacity": None,
            "commissioned_capacity": None,
            "production_capacity": None,
            "capacity_unit": "MMTPA_EQUIVALENT",
            "target_year": 2032,
            "status": "STRATEGIC_TARGET",
            "source": ("Reliance Industries Integrated Annual Report " "FY2025-26"),
            "reliability": 0.90,
        },
        # ----------------------------------------------------
        # REPORTED NEW ENERGY-RELATED NET ASSETS
        # ----------------------------------------------------
        #
        # These are accounting net-asset observations.
        # They are NOT automatically additive because
        # subsidiary / ownership overlap must be reviewed.
        # ----------------------------------------------------
        "reported_net_assets": {
            "reliance_new_energy": 17994.11,
            "reliance_new_solar_energy": 7369.62,
            "reliance_new_energy_battery_storage": 85.72,
            "source": ("Reliance Industries Integrated Annual Report " "FY2025-26"),
            "source_period": "FY2025-26",
            "reliability": 0.95,
            "treatment": "DIAGNOSTIC_ONLY_PENDING_OVERLAP_REVIEW",
        },
        # ----------------------------------------------------
        # FINANCIALS
        # ----------------------------------------------------
        #
        # No standalone New Energy revenue / EBITDA /
        # capital-employed figures have yet been authorized
        # for valuation.
        # ----------------------------------------------------
        "financials": {
            "revenue": None,
            "ebitda": None,
            "capital_employed": None,
        },
        # ----------------------------------------------------
        # SOURCE CONTROL
        # ----------------------------------------------------
        "source": ("Reliance Industries Integrated Annual Report " "FY2025-26"),
        "source_period": "FY2025-26",
        "source_type": "PRIMARY_COMPANY_DISCLOSURE",
        "reliability": 0.95,
    }
}


def _clean_symbol(symbol: str) -> str:
    return symbol.upper().strip().replace(".NS", "").replace(".BO", "")


def _is_available(value: Any) -> bool:
    """
    True when a factual value is populated.

    Zero is considered a valid factual value.
    """
    return value is not None


def get_sotp_new_energy_data(
    symbol: str,
) -> dict[str, Any]:

    base_symbol = _clean_symbol(symbol)

    data = NEW_ENERGY_DATA.get(base_symbol)

    if data is None:
        return {
            "status": "UNAVAILABLE",
            "symbol": base_symbol,
            "message": ("New Energy SOTP data is not configured " "for this company."),
        }

    investment = data.get("investment", {})
    solar = data.get("solar", {})
    battery = data.get("battery", {})
    electrolyser = data.get("electrolyser", {})
    green_hydrogen = data.get("green_hydrogen", {})
    net_assets = data.get("reported_net_assets", {})
    financials = data.get("financials", {})

    # --------------------------------------------------------
    # FACT COVERAGE
    # --------------------------------------------------------

    factual_values = [
        investment.get("announced_investment"),
        investment.get("committed_investment"),
        investment.get("capital_deployed"),
        investment.get("capital_employed"),
        solar.get("planned_capacity_gw"),
        solar.get("under_construction_capacity_gw"),
        solar.get("commissioned_capacity_gw"),
        solar.get("reported_initial_production_mwp"),
        battery.get("planned_capacity_gwh"),
        battery.get("under_construction_capacity_gwh"),
        battery.get("commissioned_capacity_gwh"),
        electrolyser.get("planned_capacity_gw"),
        electrolyser.get("commissioned_capacity_gw"),
        green_hydrogen.get("planned_capacity"),
        green_hydrogen.get("commissioned_capacity"),
        net_assets.get("reliance_new_energy"),
        net_assets.get("reliance_new_solar_energy"),
        net_assets.get("reliance_new_energy_battery_storage"),
        financials.get("revenue"),
        financials.get("ebitda"),
        financials.get("capital_employed"),
    ]

    available_fact_count = sum(_is_available(value) for value in factual_values)

    total_fact_count = len(factual_values)

    fact_coverage = available_fact_count / total_fact_count if total_fact_count > 0 else 0.0

    # --------------------------------------------------------
    # NET-ASSET DIAGNOSTIC
    # --------------------------------------------------------

    net_asset_values = [
        net_assets.get("reliance_new_energy"),
        net_assets.get("reliance_new_solar_energy"),
        net_assets.get("reliance_new_energy_battery_storage"),
    ]

    reported_net_asset_total = sum(
        value for value in net_asset_values if isinstance(value, (int, float))
    )

    # --------------------------------------------------------
    # VALUATION READINESS
    # --------------------------------------------------------
    #
    # Source data now exists, but the segment is NOT yet
    # valuation-ready.
    #
    # We still need an explicit strategic valuation policy
    # and overlap checks before authorizing New Energy EV.
    # --------------------------------------------------------

    source_data_available = available_fact_count > 0

    valuation_ready = False

    status_view = (
        "FACTUAL_DATA_AVAILABLE_VALUATION_PENDING"
        if source_data_available
        else "SOURCE_DATA_REQUIRED"
    )

    return {
        "status": "OK",
        "version": "V5.0",
        "symbol": base_symbol,
        "segment": data.get("segment"),
        "currency": data.get("currency"),
        "unit": data.get("unit"),
        "valuation_method": data.get("valuation_method"),
        "investment": investment,
        "operating_assets": {
            "solar": solar,
            "battery": battery,
            "electrolyser": electrolyser,
            "green_hydrogen": green_hydrogen,
        },
        "reported_net_assets": net_assets,
        "reported_net_asset_total": round(
            reported_net_asset_total,
            2,
        ),
        "reported_net_asset_total_is_additive": False,
        "financials": financials,
        "source": data.get("source"),
        "source_period": data.get("source_period"),
        "source_type": data.get("source_type"),
        "reliability": data.get("reliability"),
        "available_fact_count": (available_fact_count),
        "total_fact_count": total_fact_count,
        "fact_coverage": round(
            fact_coverage,
            4,
        ),
        "fact_coverage_percent": round(
            fact_coverage * 100.0,
            1,
        ),
        "source_data_available": (source_data_available),
        "valuation_ready": valuation_ready,
        "status_view": status_view,
        "warnings": [
            (
                "The ₹75,000 crore clean-energy commitment "
                "must not be treated as New Energy "
                "enterprise value."
            ),
            (
                "Planned, under-construction and "
                "commissioned manufacturing capacities "
                "must remain distinct."
            ),
            (
                "The reported 200 MWp HJT module production "
                "is an operating milestone and is not "
                "treated as 0.2 GW of annual commissioned "
                "manufacturing capacity."
            ),
            (
                "Reported subsidiary net assets are "
                "diagnostic only until ownership and "
                "consolidation overlap are reviewed."
            ),
            (
                "Strategic valuation assumptions must be "
                "implemented separately from this factual "
                "data service."
            ),
        ],
    }
