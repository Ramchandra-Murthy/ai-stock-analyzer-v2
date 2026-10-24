import math


def _safe_float(value):
    """Convert a value to a finite float or return None."""
    try:
        value = float(value)

        if math.isnan(value) or math.isinf(value):
            return None

        return value

    except (TypeError, ValueError):
        return None


def _clamp(value, minimum, maximum):
    """Restrict a number to a sensible range."""
    return max(minimum, min(value, maximum))


def generate_valuation_benchmarks(data):
    """
    Valuation Benchmark Layer V4.

    Produces fair-multiple anchors for:
        - P/E
        - Forward P/E
        - P/B
        - EV/EBITDA

    IMPORTANT:
    This first version does NOT claim to contain live
    peer-group or sector median multiples.

    Benchmark sources are explicitly identified so the
    valuation engine knows how much confidence to place
    in each benchmark.
    """

    if not isinstance(data, dict):
        return {
            "status": "UNAVAILABLE",
            "message": "Invalid company data.",
        }

    sector = str(data.get("sector", "Unknown")).strip()

    industry = str(data.get("industry", "Unknown")).strip()

    trailing_pe = _safe_float(data.get("pe"))

    forward_pe = _safe_float(data.get("forward_pe"))

    pb = _safe_float(data.get("pb"))

    ev_ebitda = _safe_float(data.get("enterprise_to_ebitda"))

    roe = _safe_float(data.get("roe"))

    revenue_growth = _safe_float(data.get("revenue_growth"))

    earnings_growth = _safe_float(data.get("earnings_growth"))

    debt_to_equity = _safe_float(data.get("debt_to_equity"))

    # ======================================================
    # P/E BENCHMARK
    # ======================================================

    if trailing_pe is not None and trailing_pe > 0 and forward_pe is not None and forward_pe > 0:
        pe_benchmark = trailing_pe * 0.40 + forward_pe * 0.60

        pe_source = "Company trailing/forward earnings anchor"

        pe_reliability = 0.55

    elif forward_pe is not None and forward_pe > 0:

        pe_benchmark = forward_pe

        pe_source = "Company forward earnings anchor"
        pe_reliability = 0.45

    elif trailing_pe is not None and trailing_pe > 0:

        pe_benchmark = trailing_pe

        pe_source = "Company trailing earnings anchor"
        pe_reliability = 0.40

    else:

        pe_benchmark = None
        pe_source = "Unavailable"
        pe_reliability = 0.0

    if pe_benchmark is not None:
        pe_benchmark = _clamp(
            pe_benchmark,
            6.0,
            40.0,
        )

    # ======================================================
    # FORWARD P/E BENCHMARK
    # ======================================================

    if forward_pe is not None and forward_pe > 0:

        forward_pe_benchmark = forward_pe

        forward_pe_source = "Company forward earnings anchor"

        forward_pe_reliability = 0.50

    elif pe_benchmark is not None:

        forward_pe_benchmark = pe_benchmark

        forward_pe_source = "Fallback from earnings benchmark"

        forward_pe_reliability = 0.30

    else:

        forward_pe_benchmark = None
        forward_pe_source = "Unavailable"
        forward_pe_reliability = 0.0

    # ======================================================
    # P/B BENCHMARK
    # ======================================================

    if pb is not None and pb > 0:

        pb_benchmark = pb

        pb_source = "Company book-value anchor"
        pb_reliability = 0.35

        # Give profitable companies a modest quality
        # adjustment, without allowing extreme values.

        if roe is not None:

            if roe >= 0.20:
                pb_benchmark *= 1.10

            elif roe >= 0.15:
                pb_benchmark *= 1.05

            elif roe < 0.08:
                pb_benchmark *= 0.90

        pb_benchmark = _clamp(
            pb_benchmark,
            0.5,
            8.0,
        )

    else:

        pb_benchmark = None
        pb_source = "Unavailable"
        pb_reliability = 0.0

    # ======================================================
    # EV / EBITDA BENCHMARK
    # ======================================================

    if ev_ebitda is not None and ev_ebitda > 0:

        ev_ebitda_benchmark = ev_ebitda

        ev_ebitda_source = "Company enterprise-value anchor"

        ev_ebitda_reliability = 0.45

        # Growth adjustment

        if revenue_growth is not None:

            if revenue_growth >= 0.20:
                ev_ebitda_benchmark *= 1.05

            elif revenue_growth < 0:
                ev_ebitda_benchmark *= 0.95

        # Leverage adjustment.
        # Yahoo debtToEquity is often percentage-style,
        # e.g. 36.65 means approximately 0.37x.

        if debt_to_equity is not None:

            normalized_de = debt_to_equity / 100.0

            if normalized_de > 1.5:
                ev_ebitda_benchmark *= 0.90

            elif normalized_de < 0.50:
                ev_ebitda_benchmark *= 1.03

        ev_ebitda_benchmark = _clamp(
            ev_ebitda_benchmark,
            4.0,
            25.0,
        )

    else:

        ev_ebitda_benchmark = None
        ev_ebitda_source = "Unavailable"
        ev_ebitda_reliability = 0.0

    # ======================================================
    # DATA QUALITY
    # ======================================================

    available_methods = sum(
        value is not None
        for value in [
            pe_benchmark,
            forward_pe_benchmark,
            pb_benchmark,
            ev_ebitda_benchmark,
        ]
    )

    if available_methods == 4:
        data_quality = "GOOD"

    elif available_methods >= 2:
        data_quality = "MODERATE"

    elif available_methods == 1:
        data_quality = "WEAK"

    else:
        data_quality = "INSUFFICIENT"

    # ======================================================
    # WARNINGS
    # ======================================================

    warnings = [
        (
            "V4 benchmark values currently use company-derived "
            "anchors rather than independent peer or sector medians."
        ),
        (
            "Company-derived benchmark multiples should receive "
            "lower valuation weights until independent benchmark "
            "data is available."
        ),
    ]

    if earnings_growth is not None and earnings_growth < 0:
        warnings.append("Historical earnings growth is negative.")

    # ======================================================
    # RETURN
    # ======================================================

    return {
        "status": "OK",
        "sector": sector,
        "industry": industry,
        "pe": {
            "multiple": (round(pe_benchmark, 2) if pe_benchmark is not None else None),
            "source": pe_source,
            "reliability": pe_reliability,
        },
        "forward_pe": {
            "multiple": (
                round(forward_pe_benchmark, 2) if forward_pe_benchmark is not None else None
            ),
            "source": forward_pe_source,
            "reliability": forward_pe_reliability,
        },
        "pb": {
            "multiple": (round(pb_benchmark, 2) if pb_benchmark is not None else None),
            "source": pb_source,
            "reliability": pb_reliability,
        },
        "ev_ebitda": {
            "multiple": (
                round(ev_ebitda_benchmark, 2) if ev_ebitda_benchmark is not None else None
            ),
            "source": ev_ebitda_source,
            "reliability": ev_ebitda_reliability,
        },
        "available_methods": available_methods,
        "data_quality": data_quality,
        "warnings": warnings,
    }
