import math


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
# MANUAL / REPORTED SEGMENT DATA
# ==========================================================
#
# IMPORTANT:
# Values are deliberately None at this stage.
#
# We will populate them only from identifiable financial
# disclosures or explicit valuation assumptions.
#
# Monetary units will be INR crore unless otherwise stated.
# ==========================================================


SOTP_SEGMENT_DATA = {
    "RELIANCE": {
        "currency": "INR",
        "unit": "crore",
        "period": "FY2025-26",
        "segments": {
            "o2c": {
                "metric_name": "EBITDA",
                "value": 60546,
                "source": ("Reliance Industries Integrated Annual " "Report FY2025-26"),
                "reliability": 0.95,
            },
            "digital": {
                "metric_name": "EBITDA",
                "value": 76560,
                "source": ("Reliance Industries Integrated Annual " "Report FY2025-26"),
                "reliability": 0.95,
            },
            "retail": {
                "metric_name": "EBITDA",
                "value": 27034,
                "source": ("Reliance Industries Integrated Annual " "Report FY2025-26"),
                "reliability": 0.95,
            },
            "upstream": {
                "metric_name": "EBITDA",
                "value": 19050,
                "source": ("Reliance Industries Integrated Annual " "Report FY2025-26"),
                "reliability": 0.95,
            },
            "new_energy": {
                "metric_name": "Strategic Value",
                "value": None,
                "source": None,
                "reliability": None,
            },
            "other": {
                "metric_name": "Asset / Investment Value",
                "value": None,
                "source": None,
                "reliability": None,
            },
        },
    },
}


def get_sotp_segment_data(symbol):
    """
    Return structured SOTP financial inputs.

    No missing financial value is estimated automatically.
    """

    base_symbol = _clean_symbol(symbol)

    company_block = SOTP_SEGMENT_DATA.get(base_symbol)

    if not isinstance(company_block, dict):
        return {
            "status": "UNAVAILABLE",
            "symbol": base_symbol,
            "message": ("No SOTP segment financial data is configured " f"for {base_symbol}."),
        }

    raw_segments = company_block.get(
        "segments",
        {},
    )

    if not isinstance(raw_segments, dict):
        raw_segments = {}

    segments = {}

    available_count = 0

    for segment_key, raw_block in raw_segments.items():

        if not isinstance(raw_block, dict):
            raw_block = {}

        value = _safe_float(raw_block.get("value"))

        reliability = _safe_float(raw_block.get("reliability"))

        if reliability is not None:
            reliability = max(
                0.0,
                min(1.0, reliability),
            )

        available = value is not None

        if available:
            available_count += 1

        segments[segment_key] = {
            "metric_name": raw_block.get("metric_name"),
            "value": value,
            "source": raw_block.get("source"),
            "reliability": reliability,
            "available": available,
        }

    total_segments = len(segments)

    coverage = available_count / total_segments if total_segments > 0 else 0.0

    return {
        "status": "OK",
        "symbol": base_symbol,
        "currency": company_block.get(
            "currency",
            "INR",
        ),
        "unit": company_block.get(
            "unit",
            "crore",
        ),
        "period": company_block.get("period"),
        "segment_count": total_segments,
        "available_segment_count": available_count,
        "coverage": round(
            coverage,
            4,
        ),
        "coverage_percent": round(
            coverage * 100.0,
            1,
        ),
        "segments": segments,
    }
