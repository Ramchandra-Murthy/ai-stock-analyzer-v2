import math

from services.sotp_equity_bridge_service import (
    generate_sotp_equity_bridge,
)

# ==========================================================
# HELPERS
# ==========================================================


def _safe_float(value):
    """Convert a value to a finite float or return None."""

    try:
        value = float(value)

        if math.isnan(value) or math.isinf(value):
            return None

        return value

    except (TypeError, ValueError):
        return None


def _valid_positive(value):
    """Return positive finite float or None."""

    value = _safe_float(value)

    if value is None or value <= 0:
        return None

    return value


def _clean_symbol(symbol):
    """Normalize NSE symbol."""

    if not symbol:
        return ""

    symbol = str(symbol).strip().upper()

    if symbol.endswith(".NS"):
        symbol = symbol[:-3]

    return symbol


# ==========================================================
# SOTP COMPANY CONFIGURATION
# ==========================================================

SOTP_CONFIG = {
    "RELIANCE": {
        "company": "Reliance Industries Limited",
        "enabled": True,
        "profile": "HIGHLY DIVERSIFIED",
        "segments": {
            "o2c": {
                "name": "Oil-to-Chemicals",
                "valuation_method": "EV/EBITDA",
            },
            "digital": {
                "name": "Digital Services / Jio",
                "valuation_method": "EV/EBITDA",
            },
            "retail": {
                "name": "Retail",
                "valuation_method": "EV/EBITDA",
            },
            "upstream": {
                "name": "Oil & Gas Exploration and Production",
                "valuation_method": "EV/EBITDA",
            },
            "new_energy": {
                "name": "New Energy",
                "valuation_method": "STRATEGIC_VALUE",
            },
            "other": {
                "name": "Other Businesses and Investments",
                "valuation_method": "ASSET_VALUE",
            },
        },
    },
}


# ==========================================================
# CONFIGURATION
# ==========================================================


def get_sotp_configuration(symbol):
    """
    Return SOTP configuration for a company.
    """

    base_symbol = _clean_symbol(symbol)

    config = SOTP_CONFIG.get(base_symbol)

    if not isinstance(config, dict):
        return {
            "status": "UNAVAILABLE",
            "symbol": base_symbol,
            "eligible": False,
            "message": ("No SOTP configuration is available for " f"{base_symbol}."),
        }

    if not config.get("enabled", False):
        return {
            "status": "UNAVAILABLE",
            "symbol": base_symbol,
            "eligible": False,
            "message": (f"SOTP valuation is disabled for {base_symbol}."),
        }

    return {
        "status": "OK",
        "symbol": base_symbol,
        "eligible": True,
        "company": config.get("company", base_symbol),
        "profile": config.get("profile", "DIVERSIFIED"),
        "segments": config.get("segments", {}),
    }


# ==========================================================
# SEGMENT TEMPLATE
# ==========================================================


def _build_segment_template(segment_key, segment_config):
    """
    Build an empty segment valuation record.

    Financial inputs and valuation multiples will be added
    in later V5 stages.
    """

    if not isinstance(segment_config, dict):
        segment_config = {}

    return {
        "segment_key": segment_key,
        "name": segment_config.get(
            "name",
            segment_key,
        ),
        "valuation_method": segment_config.get(
            "valuation_method",
            "UNKNOWN",
        ),
        "financial_metric": None,
        "financial_metric_name": None,
        "valuation_multiple": None,
        "enterprise_value": None,
        "equity_value": None,
        "reliability": None,
        "source": None,
        "status": "PENDING",
    }


# ==========================================================
# SOTP ENGINE V5
# ==========================================================


def generate_sotp_valuation(symbol, company_data=None):
    """
    Final Sum-of-the-Parts Valuation Engine V5.

    Responsibilities:
        - validate SOTP eligibility
        - consume the V5 scenario equity bridge
        - expose operating segment valuations
        - expose New Energy Bear/Base/Bull scenarios
        - expose authorized equity-bridge adjustments
        - calculate scenario equity values
        - calculate scenario fair values per share
        - expose pending valuation items
        - expose confidence and valuation status

    This service does not independently recalculate
    segment EV, New Energy value, or bridge adjustments.
    Those calculations remain owned by their respective
    lower-level V5 services.
    """

    base_symbol = _clean_symbol(symbol)

    # ======================================================
    # 1. CONFIGURATION / ELIGIBILITY
    # ======================================================

    configuration = get_sotp_configuration(base_symbol)

    if configuration.get("status") != "OK":
        return configuration

    # ======================================================
    # 2. FINAL V5 EQUITY BRIDGE
    # ======================================================

    bridge = generate_sotp_equity_bridge(base_symbol)

    if not isinstance(bridge, dict) or bridge.get("status") != "OK":
        return {
            "status": "ERROR",
            "version": "V5.0",
            "symbol": base_symbol,
            "company": configuration.get(
                "company",
                base_symbol,
            ),
            "eligible": True,
            "message": "V5 SOTP equity bridge is unavailable.",
            "bridge": bridge,
        }

    # ======================================================
    # 3. COMPONENTS
    # ======================================================

    components = bridge.get("components", {})

    if not isinstance(components, dict):
        components = {}

    operating = components.get("operating", {})

    if not isinstance(operating, dict):
        operating = {}

    operating_segments = operating.get(
        "segments",
        {},
    )

    if not isinstance(operating_segments, dict):
        operating_segments = {}

    # ======================================================
    # 4. BUILD FINAL SEGMENT VIEW
    # ======================================================

    segments_config = configuration.get(
        "segments",
        {},
    )

    if not isinstance(segments_config, dict):
        segments_config = {}

    segments = {}

    for segment_key, segment_config in segments_config.items():

        template = _build_segment_template(
            segment_key,
            segment_config,
        )

        operating_result = operating_segments.get(segment_key)

        if isinstance(operating_result, dict):

            template.update(
                {
                    "financial_metric": (_safe_float(operating_result.get("metric_value"))),
                    "financial_metric_name": (operating_result.get("metric_name")),
                    "valuation_multiple": (_safe_float(operating_result.get("benchmark_multiple"))),
                    "enterprise_value": (_safe_float(operating_result.get("enterprise_value"))),
                    "reliability": (_safe_float(operating_result.get("reliability"))),
                    "source": (operating_result.get("financial_source")),
                    "benchmark_source": (operating_result.get("benchmark_source")),
                    "status": (
                        operating_result.get(
                            "status",
                            "PENDING",
                        )
                    ),
                }
            )

        elif segment_key == "new_energy":

            new_energy = bridge.get(
                "new_energy",
                {},
            )

            template.update(
                {
                    "status": (
                        "SCENARIO_VALUED"
                        if new_energy.get("scenario_range_authorized")
                        else "PENDING"
                    ),
                    "scenario_values": (
                        new_energy.get(
                            "scenario_values",
                            {},
                        )
                    ),
                    "source": ("V5 New Energy scenario policy"),
                }
            )

        elif segment_key == "other":

            template.update(
                {
                    "status": "PENDING_POLICY",
                    "source": ("V5 investment and asset " "classification services"),
                }
            )

        segments[segment_key] = template

    # ======================================================
    # 5. SCENARIO OUTPUT
    # ======================================================

    raw_scenarios = bridge.get(
        "scenarios",
        {},
    )

    if not isinstance(raw_scenarios, dict):
        raw_scenarios = {}

    scenarios = {}

    for scenario_name in (
        "BEAR",
        "BASE",
        "BULL",
    ):

        scenario = raw_scenarios.get(scenario_name)

        if not isinstance(scenario, dict):
            continue

        scenarios[scenario_name] = {
            "operating_enterprise_value": (_safe_float(scenario.get("operating_enterprise_value"))),
            "new_energy_enterprise_value": (
                _safe_float(scenario.get("new_energy_enterprise_value"))
            ),
            "gross_enterprise_value": (_safe_float(scenario.get("gross_enterprise_value"))),
            "equity_bridge_adjustment": (_safe_float(scenario.get("equity_bridge_adjustment"))),
            "equity_value": (_safe_float(scenario.get("equity_value"))),
            "fair_value_per_share": (_safe_float(scenario.get("fair_value_per_share"))),
            "upside_percent": (_safe_float(scenario.get("upside_percent"))),
        }

    # ======================================================
    # 6. BASE CASE CONVENIENCE FIELDS
    # ======================================================

    base_case = scenarios.get(
        "BASE",
        {},
    )

    base_gross_ev = _safe_float(base_case.get("gross_enterprise_value"))

    base_equity_value = _safe_float(base_case.get("equity_value"))

    base_fair_value = _safe_float(base_case.get("fair_value_per_share"))

    base_upside = _safe_float(base_case.get("upside_percent"))

    # ======================================================
    # 7. EQUITY-BRIDGE VIEW
    # ======================================================

    equity_bridge = bridge.get(
        "equity_bridge",
        {},
    )

    if not isinstance(equity_bridge, dict):
        equity_bridge = {}

    # ======================================================
    # 8. FINAL OUTPUT
    # ======================================================

    return {
        "status": "OK",
        "version": "V5.0",
        "symbol": base_symbol,
        "company": configuration.get(
            "company",
            base_symbol,
        ),
        "eligible": True,
        "profile": configuration.get(
            "profile",
            "DIVERSIFIED",
        ),
        "currency": bridge.get(
            "currency",
            "INR",
        ),
        "unit": bridge.get(
            "unit",
            "crore",
        ),
        "period": bridge.get("period"),
        "current_price": (_safe_float(bridge.get("current_price"))),
        "shares_outstanding": (_safe_float(bridge.get("shares_outstanding"))),
        "segment_count": len(segments),
        "segments": segments,
        "operating_enterprise_value": (_safe_float(bridge.get("operating_enterprise_value"))),
        "gross_enterprise_value": (base_gross_ev),
        "equity_bridge_adjustment": (_safe_float(equity_bridge.get("authorized_adjustment"))),
        "equity_value": (base_equity_value),
        "fair_value_per_share": (base_fair_value),
        "upside_percent": (base_upside),
        "scenarios": scenarios,
        "confidence": bridge.get("confidence"),
        "confidence_score": (_safe_float(bridge.get("confidence_score"))),
        "valuation_status": bridge.get(
            "valuation_status",
            "PROVISIONAL",
        ),
        "pending_exposure": (_safe_float(equity_bridge.get("pending_exposure"))),
        "pending_item_count": (
            equity_bridge.get(
                "pending_item_count",
                0,
            )
        ),
        "pending_items": (
            equity_bridge.get(
                "pending_items",
                [],
            )
        ),
        "interpretation": (
            "SOTP V5 values Reliance's operating "
            "businesses using validated segment "
            "benchmarks, adds the authorized New "
            "Energy Bear/Base/Bull scenario values, "
            "and applies only explicitly authorized "
            "equity-bridge adjustments. The BASE "
            "scenario is exposed as the headline "
            "valuation while Bear and Bull cases "
            "remain available for scenario analysis."
        ),
        "warnings": bridge.get(
            "warnings",
            [],
        ),
        "components": components,
    }
