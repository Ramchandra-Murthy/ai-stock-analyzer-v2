import math

from services.sotp_benchmark_service import (
    generate_validated_sotp_benchmarks,
)
from services.sotp_segment_data_service import (
    get_sotp_segment_data,
)

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
# SINGLE SEGMENT VALUATION
# ==========================================================


def _value_operating_segment(
    segment_key,
    financial_block,
    benchmark_block,
):
    """
    Value one operating segment using:

        EBITDA × EV/EBITDA

    Monetary values remain in the same unit as the
    segment financial input, currently INR crore.
    """

    if not isinstance(financial_block, dict):
        financial_block = {}

    if not isinstance(benchmark_block, dict):
        benchmark_block = {}

    metric_name = financial_block.get("metric_name")

    metric_value = _safe_float(financial_block.get("value"))

    data_reliability = _safe_float(financial_block.get("reliability"))

    method = benchmark_block.get("method")

    multiple = _safe_float(benchmark_block.get("benchmark_multiple"))

    benchmark_reliability = _safe_float(benchmark_block.get("reliability"))

    # ------------------------------------------------------
    # FINANCIAL DATA CHECK
    # ------------------------------------------------------

    if metric_value is None:
        return {
            "status": "PENDING",
            "segment": segment_key,
            "method": method,
            "metric_name": metric_name,
            "metric_value": None,
            "benchmark_multiple": multiple,
            "enterprise_value": None,
            "reliability": None,
            "message": "Segment financial input is unavailable.",
        }

    # ------------------------------------------------------
    # METHOD CHECK
    # ------------------------------------------------------

    if method != "EV/EBITDA":
        return {
            "status": "PENDING",
            "segment": segment_key,
            "method": method,
            "metric_name": metric_name,
            "metric_value": metric_value,
            "benchmark_multiple": multiple,
            "enterprise_value": None,
            "reliability": None,
            "message": (f"{method} is not an operating " "EV/EBITDA valuation."),
        }

    if metric_name != "EBITDA":
        return {
            "status": "UNAVAILABLE",
            "segment": segment_key,
            "method": method,
            "metric_name": metric_name,
            "metric_value": metric_value,
            "benchmark_multiple": multiple,
            "enterprise_value": None,
            "reliability": 0.0,
            "message": ("EV/EBITDA valuation requires " "an EBITDA financial input."),
        }

    # ------------------------------------------------------
    # BENCHMARK CHECK
    # ------------------------------------------------------

    if benchmark_block.get("status") != "OK" or multiple is None or multiple <= 0:
        return {
            "status": "UNAVAILABLE",
            "segment": segment_key,
            "method": method,
            "metric_name": metric_name,
            "metric_value": metric_value,
            "benchmark_multiple": multiple,
            "enterprise_value": None,
            "reliability": 0.0,
            "message": ("Valid segment benchmark is unavailable."),
        }

    # ------------------------------------------------------
    # ENTERPRISE VALUE
    # ------------------------------------------------------

    enterprise_value = metric_value * multiple

    # ------------------------------------------------------
    # COMBINED RELIABILITY
    # ------------------------------------------------------

    if data_reliability is None:
        data_reliability = 0.0

    if benchmark_reliability is None:
        benchmark_reliability = 0.0

    data_reliability = max(
        0.0,
        min(1.0, data_reliability),
    )

    benchmark_reliability = max(
        0.0,
        min(1.0, benchmark_reliability),
    )

    # Conservative combination:
    # weak benchmark quality should not be hidden by
    # excellent reported financial data.
    combined_reliability = math.sqrt(data_reliability * benchmark_reliability)

    return {
        "status": "OK",
        "segment": segment_key,
        "method": method,
        "metric_name": metric_name,
        "metric_value": round(
            metric_value,
            2,
        ),
        "financial_source": financial_block.get("source"),
        "data_reliability": round(
            data_reliability,
            4,
        ),
        "raw_benchmark_multiple": benchmark_block.get("raw_benchmark_multiple"),
        "benchmark_multiple": round(
            multiple,
            4,
        ),
        "benchmark_source": benchmark_block.get("source"),
        "benchmark_reliability": round(
            benchmark_reliability,
            4,
        ),
        "enterprise_value": round(
            enterprise_value,
            2,
        ),
        "reliability": round(
            combined_reliability,
            4,
        ),
    }


# ==========================================================
# OPERATING SOTP ENGINE
# ==========================================================


def generate_operating_sotp_valuation(symbol):
    """
    Calculate SOTP enterprise values for operating segments.

    This stage does NOT calculate:
        - New Energy value
        - Other investments
        - net debt
        - equity value
        - fair value per share
    """

    base_symbol = _clean_symbol(symbol)

    financial_data = get_sotp_segment_data(base_symbol)

    if financial_data.get("status") != "OK":
        return financial_data

    benchmark_data = generate_validated_sotp_benchmarks(base_symbol)

    if benchmark_data.get("status") != "OK":
        return benchmark_data

    financial_segments = financial_data.get(
        "segments",
        {},
    )

    benchmark_segments = benchmark_data.get(
        "segments",
        {},
    )

    if not isinstance(financial_segments, dict):
        financial_segments = {}

    if not isinstance(benchmark_segments, dict):
        benchmark_segments = {}

    # Only true operating businesses belong in the
    # EBITDA/multiple-based operating SOTP engine.
    #
    # New Energy is handled separately by the scenario engine.
    # Other businesses/investments are handled separately by
    # the investment / asset policy and equity bridge.
    segment_keys = [
        "o2c",
        "digital",
        "retail",
        "upstream",
    ]

    results = {}

    operating_enterprise_value = 0.0

    valued_count = 0

    reliability_numerator = 0.0
    reliability_denominator = 0.0

    for segment_key in segment_keys:

        financial_block = financial_segments.get(
            segment_key,
            {},
        )

        benchmark_block = benchmark_segments.get(
            segment_key,
            {},
        )

        result = _value_operating_segment(
            segment_key=segment_key,
            financial_block=financial_block,
            benchmark_block=benchmark_block,
        )

        results[segment_key] = result

        if result.get("status") != "OK":
            continue

        enterprise_value = _safe_float(result.get("enterprise_value"))

        reliability = _safe_float(result.get("reliability"))

        if enterprise_value is None:
            continue

        operating_enterprise_value += enterprise_value

        valued_count += 1

        if reliability is not None and enterprise_value > 0:
            reliability_numerator += enterprise_value * reliability

            reliability_denominator += enterprise_value

    operating_segment_count = benchmark_data.get(
        "multiple_segment_count",
        0,
    )

    coverage = valued_count / operating_segment_count if operating_segment_count > 0 else 0.0

    weighted_reliability = (
        reliability_numerator / reliability_denominator if reliability_denominator > 0 else 0.0
    )

    return {
        "status": "OK",
        "version": "V5.0",
        "symbol": base_symbol,
        "currency": financial_data.get(
            "currency",
            "INR",
        ),
        "unit": financial_data.get(
            "unit",
            "crore",
        ),
        "period": financial_data.get("period"),
        "operating_segment_count": operating_segment_count,
        "valued_operating_segment_count": valued_count,
        "operating_coverage": round(
            coverage,
            4,
        ),
        "operating_coverage_percent": round(
            coverage * 100.0,
            1,
        ),
        "operating_enterprise_value": round(
            operating_enterprise_value,
            2,
        ),
        "weighted_reliability": round(
            weighted_reliability,
            4,
        ),
        "segments": results,
    }
