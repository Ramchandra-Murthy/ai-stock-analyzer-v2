import math
import statistics

import yfinance as yf

# ==========================================================
# HELPERS
# ==========================================================


def _safe_float(value):
    """Convert value to finite float or return None."""

    try:
        value = float(value)

        if math.isnan(value) or math.isinf(value):
            return None

        return value

    except (TypeError, ValueError):
        return None


def _clean_symbol(symbol):
    """Normalize NSE symbol."""

    if not symbol:
        return ""

    symbol = str(symbol).strip().upper()

    if symbol.endswith(".NS"):
        symbol = symbol[:-3]

    return symbol


# ==========================================================
# SEGMENT BENCHMARK CONFIGURATION
# ==========================================================
#
# IMPORTANT:
#
# Multiples deliberately remain None.
#
# This layer defines:
#   - valuation method
#   - benchmark type
#   - peer universe
#
# Actual peer multiples will be calculated in the next stage.
# ==========================================================


SOTP_BENCHMARK_CONFIG = {
    "RELIANCE": {
        "o2c": {
            "method": "EV/EBITDA",
            "peer_group": [
                "IOC.NS",
                "BPCL.NS",
                "HINDPETRO.NS",
            ],
            "benchmark_multiple": None,
            "source": None,
            "reliability": None,
        },
        "digital": {
            "method": "EV/EBITDA",
            "peer_group": [
                "BHARTIARTL.NS",
            ],
            "benchmark_multiple": None,
            "source": None,
            "reliability": None,
        },
        "retail": {
            "method": "EV/EBITDA",
            "peer_group": [
                "DMART.NS",
                "TRENT.NS",
            ],
            "benchmark_multiple": None,
            "source": None,
            "reliability": None,
        },
        "upstream": {
            "method": "EV/EBITDA",
            "peer_group": [
                "ONGC.NS",
                "OIL.NS",
            ],
            "benchmark_multiple": None,
            "source": None,
            "reliability": None,
        },
        "new_energy": {
            "method": "STRATEGIC_VALUE",
            "peer_group": [],
            "benchmark_multiple": None,
            "source": None,
            "reliability": None,
        },
        "other": {
            "method": "ASSET_VALUE",
            "peer_group": [],
            "benchmark_multiple": None,
            "source": None,
            "reliability": None,
        },
    },
}

# ==========================================================
# SOTP MULTIPLE VALIDATION RANGES
# ==========================================================

SOTP_MULTIPLE_RANGES = {
    "RELIANCE": {
        "o2c": {
            "floor": 3.0,
            "cap": 10.0,
        },
        "digital": {
            "floor": 6.0,
            "cap": 18.0,
        },
        "retail": {
            "floor": 8.0,
            "cap": 30.0,
        },
        "upstream": {
            "floor": 3.0,
            "cap": 10.0,
        },
    },
}


def _validate_segment_multiple(
    symbol,
    segment_key,
    raw_multiple,
    reliability,
):
    """
    Apply explicit SOTP multiple guardrails.

    Raw peer benchmark is preserved for transparency.
    Reliability is reduced when the benchmark requires
    clipping to the configured valuation range.
    """

    base_symbol = _clean_symbol(symbol)

    raw_multiple = _safe_float(raw_multiple)
    reliability = _safe_float(reliability)

    if raw_multiple is None or raw_multiple <= 0:
        return {
            "status": "UNAVAILABLE",
            "raw_multiple": raw_multiple,
            "final_multiple": None,
            "adjusted": False,
            "reliability": 0.0,
            "message": "Invalid raw benchmark multiple.",
        }

    if reliability is None:
        reliability = 0.0

    reliability = max(
        0.0,
        min(1.0, reliability),
    )

    company_ranges = SOTP_MULTIPLE_RANGES.get(
        base_symbol,
        {},
    )

    range_config = company_ranges.get(
        segment_key,
        {},
    )

    floor = _safe_float(range_config.get("floor"))

    cap = _safe_float(range_config.get("cap"))

    # No configured range
    if floor is None or cap is None:
        return {
            "status": "OK",
            "raw_multiple": round(raw_multiple, 4),
            "floor": floor,
            "cap": cap,
            "final_multiple": round(raw_multiple, 4),
            "adjusted": False,
            "adjustment_reason": None,
            "reliability": round(reliability, 4),
        }

    if floor <= 0 or cap <= 0 or floor > cap:
        return {
            "status": "UNAVAILABLE",
            "raw_multiple": round(raw_multiple, 4),
            "floor": floor,
            "cap": cap,
            "final_multiple": None,
            "adjusted": False,
            "reliability": 0.0,
            "message": "Invalid configured multiple range.",
        }

    final_multiple = raw_multiple
    adjusted = False
    adjustment_reason = None

    if raw_multiple < floor:
        final_multiple = floor
        adjusted = True
        adjustment_reason = "RAW MULTIPLE BELOW FLOOR"

    elif raw_multiple > cap:
        final_multiple = cap
        adjusted = True
        adjustment_reason = "RAW MULTIPLE ABOVE CAP"

    # Penalize reliability when model intervention is required.
    adjusted_reliability = reliability

    if adjusted:
        adjusted_reliability *= 0.75

    return {
        "status": "OK",
        "raw_multiple": round(raw_multiple, 4),
        "floor": round(floor, 4),
        "cap": round(cap, 4),
        "final_multiple": round(final_multiple, 4),
        "adjusted": adjusted,
        "adjustment_reason": adjustment_reason,
        "pre_validation_reliability": round(
            reliability,
            4,
        ),
        "reliability": round(
            adjusted_reliability,
            4,
        ),
    }


def generate_validated_sotp_benchmarks(symbol):
    """
    Generate dynamic SOTP peer benchmarks and apply
    segment-specific multiple validation controls.
    """

    base_symbol = _clean_symbol(symbol)

    raw_result = generate_sotp_peer_benchmarks(base_symbol)

    if raw_result.get("status") != "OK":
        return raw_result

    raw_segments = raw_result.get(
        "segments",
        {},
    )

    if not isinstance(raw_segments, dict):
        raw_segments = {}

    segments = {}

    usable_count = 0
    adjusted_count = 0

    for segment_key, benchmark in raw_segments.items():

        if not isinstance(benchmark, dict):
            benchmark = {}

        method = benchmark.get("method")

        # Preserve strategic/asset methods unchanged.
        if method != "EV/EBITDA":
            segments[segment_key] = dict(benchmark)
            continue

        if benchmark.get("status") != "OK":
            segments[segment_key] = dict(benchmark)
            continue

        validation = _validate_segment_multiple(
            symbol=base_symbol,
            segment_key=segment_key,
            raw_multiple=benchmark.get("benchmark_multiple"),
            reliability=benchmark.get("reliability"),
        )

        block = dict(benchmark)

        block["raw_benchmark_multiple"] = benchmark.get("benchmark_multiple")

        block["validation"] = validation

        if validation.get("status") == "OK":

            block["benchmark_multiple"] = validation.get("final_multiple")

            block["reliability"] = validation.get("reliability")

            block["source"] = "Validated dynamic peer median"

            usable_count += 1

            if validation.get("adjusted"):
                adjusted_count += 1

        else:
            block["status"] = "UNAVAILABLE"
            block["benchmark_multiple"] = None
            block["reliability"] = 0.0

        segments[segment_key] = block

    multiple_segment_count = raw_result.get(
        "multiple_segment_count",
        0,
    )

    coverage = usable_count / multiple_segment_count if multiple_segment_count > 0 else 0.0

    return {
        "status": "OK",
        "symbol": base_symbol,
        "multiple_segment_count": multiple_segment_count,
        "usable_benchmark_count": usable_count,
        "adjusted_benchmark_count": adjusted_count,
        "benchmark_coverage": round(
            coverage,
            4,
        ),
        "benchmark_coverage_percent": round(
            coverage * 100.0,
            1,
        ),
        "segments": segments,
    }


# ==========================================================
# BENCHMARK CONFIGURATION ACCESS
# ==========================================================


def get_sotp_benchmark_configuration(symbol):
    """
    Return segment-specific SOTP benchmark configuration.
    """

    base_symbol = _clean_symbol(symbol)

    company_config = SOTP_BENCHMARK_CONFIG.get(base_symbol)

    if not isinstance(company_config, dict):
        return {
            "status": "UNAVAILABLE",
            "symbol": base_symbol,
            "message": ("No SOTP benchmark configuration is " f"available for {base_symbol}."),
        }

    segments = {}

    configured_count = 0

    for segment_key, raw_block in company_config.items():

        if not isinstance(raw_block, dict):
            raw_block = {}

        method = raw_block.get(
            "method",
            "UNKNOWN",
        )

        peer_group = raw_block.get(
            "peer_group",
            [],
        )

        if not isinstance(peer_group, list):
            peer_group = []

        benchmark_multiple = _safe_float(raw_block.get("benchmark_multiple"))

        reliability = _safe_float(raw_block.get("reliability"))

        if reliability is not None:
            reliability = max(
                0.0,
                min(1.0, reliability),
            )

        if method in {
            "STRATEGIC_VALUE",
            "ASSET_VALUE",
        }:
            configured = True

        else:
            configured = len(peer_group) > 0

        if configured:
            configured_count += 1

        segments[segment_key] = {
            "method": method,
            "peer_group": peer_group,
            "peer_count": len(peer_group),
            "benchmark_multiple": benchmark_multiple,
            "source": raw_block.get("source"),
            "reliability": reliability,
            "configured": configured,
        }

    total_segments = len(segments)

    configuration_coverage = configured_count / total_segments if total_segments > 0 else 0.0

    return {
        "status": "OK",
        "symbol": base_symbol,
        "segment_count": total_segments,
        "configured_segment_count": configured_count,
        "configuration_coverage": round(
            configuration_coverage,
            4,
        ),
        "configuration_coverage_percent": round(
            configuration_coverage * 100.0,
            1,
        ),
        "segments": segments,
    }


# ==========================================================
# PEER MULTIPLE FETCHING
# ==========================================================


def _fetch_peer_ev_ebitda(symbol):
    """
    Fetch EV/EBITDA for one listed peer.

    Returns None when Yahoo Finance does not provide a
    valid positive multiple.
    """

    try:
        ticker = yf.Ticker(symbol)

        info = ticker.info or {}

        multiple = _safe_float(info.get("enterpriseToEbitda"))

        if multiple is None:
            return None

        if multiple <= 0:
            return None

        return multiple

    except Exception:
        return None


# ==========================================================
# BENCHMARK RELIABILITY
# ==========================================================


def _benchmark_reliability(observations):
    """
    Assign reliability according to usable peer count.

    This measures benchmark breadth only.

    It does NOT yet measure:
        - business-model similarity
        - growth similarity
        - profitability similarity
        - leverage similarity
        - geographic differences
    """

    if observations >= 5:
        return 0.90

    if observations == 4:
        return 0.85

    if observations == 3:
        return 0.80

    if observations == 2:
        return 0.70

    if observations == 1:
        return 0.50

    return 0.0


# ==========================================================
# SINGLE SEGMENT BENCHMARK
# ==========================================================


def _generate_segment_peer_benchmark(
    segment_key,
    segment_config,
):
    """
    Generate an EV/EBITDA benchmark for one SOTP segment.
    """

    if not isinstance(segment_config, dict):
        return {
            "status": "UNAVAILABLE",
            "segment": segment_key,
            "message": "Invalid segment configuration.",
        }

    method = segment_config.get(
        "method",
        "UNKNOWN",
    )

    peer_group = segment_config.get(
        "peer_group",
        [],
    )

    if not isinstance(peer_group, list):
        peer_group = []

    # ------------------------------------------------------
    # NON-MULTIPLE METHODS
    # ------------------------------------------------------

    if method in {
        "STRATEGIC_VALUE",
        "ASSET_VALUE",
    }:
        return {
            "status": "PENDING",
            "segment": segment_key,
            "method": method,
            "peer_group": peer_group,
            "peer_count": len(peer_group),
            "observations": 0,
            "benchmark_multiple": None,
            "source": None,
            "reliability": None,
            "peer_values": [],
            "message": (f"{method} requires a separate valuation " "framework."),
        }

    if method != "EV/EBITDA":
        return {
            "status": "UNAVAILABLE",
            "segment": segment_key,
            "method": method,
            "message": (f"Unsupported SOTP benchmark method: {method}"),
        }

    # ------------------------------------------------------
    # FETCH PEER MULTIPLES
    # ------------------------------------------------------

    peer_values = []

    valid_multiples = []

    for peer_symbol in peer_group:

        multiple = _fetch_peer_ev_ebitda(peer_symbol)

        valid = multiple is not None

        peer_values.append(
            {
                "symbol": peer_symbol,
                "ev_ebitda": (round(multiple, 4) if multiple is not None else None),
                "valid": valid,
            }
        )

        if valid:
            valid_multiples.append(multiple)

    observations = len(valid_multiples)

    # ------------------------------------------------------
    # NO VALID DATA
    # ------------------------------------------------------

    if observations == 0:
        return {
            "status": "UNAVAILABLE",
            "segment": segment_key,
            "method": method,
            "peer_group": peer_group,
            "peer_count": len(peer_group),
            "observations": 0,
            "benchmark_multiple": None,
            "source": "Dynamic peer median",
            "reliability": 0.0,
            "peer_values": peer_values,
            "message": ("No valid positive peer EV/EBITDA " "observations are available."),
        }

    # ------------------------------------------------------
    # MEDIAN
    # ------------------------------------------------------

    benchmark_multiple = statistics.median(valid_multiples)

    reliability = _benchmark_reliability(observations)

    return {
        "status": "OK",
        "segment": segment_key,
        "method": method,
        "peer_group": peer_group,
        "peer_count": len(peer_group),
        "observations": observations,
        "benchmark_multiple": round(
            benchmark_multiple,
            4,
        ),
        "source": "Dynamic peer median",
        "reliability": round(
            reliability,
            4,
        ),
        "peer_values": peer_values,
    }


# ==========================================================
# COMPLETE SOTP BENCHMARK ENGINE
# ==========================================================


def generate_sotp_peer_benchmarks(symbol):
    """
    Generate dynamic segment-specific peer benchmarks.

    EV/EBITDA segments:
        benchmark = median valid peer EV/EBITDA

    Strategic-value and asset-value segments remain pending.
    """

    base_symbol = _clean_symbol(symbol)

    configuration = get_sotp_benchmark_configuration(base_symbol)

    if configuration.get("status") != "OK":
        return configuration

    configured_segments = configuration.get(
        "segments",
        {},
    )

    if not isinstance(configured_segments, dict):
        configured_segments = {}

    results = {}

    usable_benchmark_count = 0

    multiple_segment_count = 0

    for segment_key, segment_config in configured_segments.items():

        method = segment_config.get("method")

        if method == "EV/EBITDA":
            multiple_segment_count += 1

        benchmark = _generate_segment_peer_benchmark(
            segment_key,
            segment_config,
        )

        results[segment_key] = benchmark

        if method == "EV/EBITDA" and benchmark.get("status") == "OK":
            usable_benchmark_count += 1

    benchmark_coverage = (
        usable_benchmark_count / multiple_segment_count if multiple_segment_count > 0 else 0.0
    )

    return {
        "status": "OK",
        "symbol": base_symbol,
        "segment_count": len(results),
        "multiple_segment_count": multiple_segment_count,
        "usable_benchmark_count": usable_benchmark_count,
        "benchmark_coverage": round(
            benchmark_coverage,
            4,
        ),
        "benchmark_coverage_percent": round(
            benchmark_coverage * 100.0,
            1,
        ),
        "segments": results,
    }
