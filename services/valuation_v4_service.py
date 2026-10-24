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


def _valid_positive(value):
    value = _safe_float(value)

    if value is None or value <= 0:
        return None

    return value


def _calculate_return(fair_value, current_price):
    """Return upside/downside percentage."""
    if fair_value is None or current_price is None:
        return None

    if current_price <= 0:
        return None

    return ((fair_value / current_price) - 1.0) * 100.0


def _valuation_status(upside):
    """Classify composite valuation."""
    if upside is None:
        return "UNKNOWN"

    if upside >= 30:
        return "DEEPLY UNDERVALUED"

    if upside >= 15:
        return "UNDERVALUED"

    if upside >= 5:
        return "SLIGHTLY UNDERVALUED"

    if upside > -5:
        return "FAIRLY VALUED"

    if upside > -15:
        return "SLIGHTLY OVERVALUED"

    if upside > -30:
        return "OVERVALUED"

    return "DEEPLY OVERVALUED"


def _confidence_label(score):
    """Convert 0-100 confidence score into label."""
    if score >= 75:
        return "HIGH"

    if score >= 55:
        return "MODERATE"

    if score >= 35:
        return "LOW"

    return "VERY LOW"


def generate_valuation_v4(data, benchmarks):
    """
    Multi-Method Valuation Engine V4.

    Methods:
        1. Trailing earnings valuation
        2. Forward earnings valuation
        3. Price-to-book valuation
        4. EV/EBITDA valuation
        5. Free-cash-flow yield valuation

    Each method receives a reliability-adjusted weight.

    NOTE:
    Benchmark V4 currently uses company-derived anchors.
    Consequently, confidence is deliberately constrained.
    """

    if not isinstance(data, dict):
        return {
            "status": "UNAVAILABLE",
            "message": "Invalid company data.",
        }

    if not isinstance(benchmarks, dict):
        return {
            "status": "UNAVAILABLE",
            "message": "Valuation benchmarks unavailable.",
        }

    if benchmarks.get("status") != "OK":
        return {
            "status": "UNAVAILABLE",
            "message": benchmarks.get(
                "message",
                "Valuation benchmarks unavailable.",
            ),
        }

    # ======================================================
    # CORE DATA
    # ======================================================

    current_price = _valid_positive(data.get("price"))

    eps = _valid_positive(data.get("eps"))

    forward_eps = _valid_positive(data.get("forward_eps"))

    book_value = _valid_positive(data.get("book_value"))

    ebitda = _valid_positive(data.get("ebitda"))

    shares = _valid_positive(data.get("shares_outstanding"))

    total_debt = _safe_float(data.get("total_debt"))

    total_cash = _safe_float(data.get("total_cash"))

    free_cash_flow = _valid_positive(data.get("free_cash_flow"))

    if current_price is None:
        return {
            "status": "UNAVAILABLE",
            "message": "Current market price unavailable.",
        }

    # ======================================================
    # METHOD CONTAINER
    # ======================================================

    methods = {}

    # ======================================================
    # 1. TRAILING P/E VALUATION
    # ======================================================

    pe_info = benchmarks.get("pe", {})

    pe_multiple = _valid_positive(pe_info.get("multiple"))

    pe_reliability = _safe_float(pe_info.get("reliability"))

    if (
        eps is not None
        and pe_multiple is not None
        and pe_reliability is not None
        and pe_reliability > 0
    ):
        pe_fair_value = eps * pe_multiple

        methods["trailing_pe"] = {
            "name": "Trailing P/E",
            "fair_value": pe_fair_value,
            "upside_percent": _calculate_return(
                pe_fair_value,
                current_price,
            ),
            "benchmark": pe_multiple,
            "benchmark_label": f"{pe_multiple:.2f}x",
            "source": pe_info.get(
                "source",
                "Unknown",
            ),
            "reliability": pe_reliability,
            "base_weight": 0.25,
        }

    # ======================================================
    # 2. FORWARD P/E VALUATION
    # ======================================================

    forward_info = benchmarks.get(
        "forward_pe",
        {},
    )

    forward_multiple = _valid_positive(forward_info.get("multiple"))

    forward_reliability = _safe_float(forward_info.get("reliability"))

    if (
        forward_eps is not None
        and forward_multiple is not None
        and forward_reliability is not None
        and forward_reliability > 0
    ):
        forward_fair_value = forward_eps * forward_multiple

        methods["forward_pe"] = {
            "name": "Forward P/E",
            "fair_value": forward_fair_value,
            "upside_percent": _calculate_return(
                forward_fair_value,
                current_price,
            ),
            "benchmark": forward_multiple,
            "benchmark_label": (f"{forward_multiple:.2f}x"),
            "source": forward_info.get(
                "source",
                "Unknown",
            ),
            "reliability": forward_reliability,
            "base_weight": 0.25,
        }

    # ======================================================
    # 3. P/B VALUATION
    # ======================================================

    pb_info = benchmarks.get("pb", {})

    pb_multiple = _valid_positive(pb_info.get("multiple"))

    pb_reliability = _safe_float(pb_info.get("reliability"))

    if (
        book_value is not None
        and pb_multiple is not None
        and pb_reliability is not None
        and pb_reliability > 0
    ):
        pb_fair_value = book_value * pb_multiple

        methods["pb"] = {
            "name": "Price / Book",
            "fair_value": pb_fair_value,
            "upside_percent": _calculate_return(
                pb_fair_value,
                current_price,
            ),
            "benchmark": pb_multiple,
            "benchmark_label": (f"{pb_multiple:.2f}x"),
            "source": pb_info.get(
                "source",
                "Unknown",
            ),
            "reliability": pb_reliability,
            "base_weight": 0.10,
        }

    # ======================================================
    # 4. EV / EBITDA VALUATION
    # ======================================================

    ev_info = benchmarks.get(
        "ev_ebitda",
        {},
    )

    ev_multiple = _valid_positive(ev_info.get("multiple"))

    ev_reliability = _safe_float(ev_info.get("reliability"))

    if (
        ebitda is not None
        and shares is not None
        and ev_multiple is not None
        and ev_reliability is not None
        and ev_reliability > 0
    ):
        debt = total_debt if total_debt is not None else 0.0

        cash = total_cash if total_cash is not None else 0.0

        implied_enterprise_value = ebitda * ev_multiple

        implied_equity_value = implied_enterprise_value - debt + cash

        if implied_equity_value > 0:

            ev_fair_value = implied_equity_value / shares

            methods["ev_ebitda"] = {
                "name": "EV / EBITDA",
                "fair_value": ev_fair_value,
                "upside_percent": _calculate_return(
                    ev_fair_value,
                    current_price,
                ),
                "benchmark": ev_multiple,
                "benchmark_label": (f"{ev_multiple:.2f}x"),
                "source": ev_info.get(
                    "source",
                    "Unknown",
                ),
                "reliability": ev_reliability,
                "base_weight": 0.25,
            }

    # ======================================================
    # 5. FREE CASH FLOW YIELD VALUATION
    # ======================================================
    #
    # This is NOT a full DCF.
    #
    # We use normalized equity FCF yield as a secondary
    # valuation signal.
    #
    # 5% required FCF yield corresponds to approximately
    # 20x FCF.
    #
    # Because this is currently a generic assumption,
    # reliability remains deliberately low.
    # ======================================================

    if free_cash_flow is not None and shares is not None:
        fcf_per_share = free_cash_flow / shares

        required_fcf_yield = 0.05

        fcf_fair_value = fcf_per_share / required_fcf_yield

        methods["fcf_yield"] = {
            "name": "FCF Yield",
            "fair_value": fcf_fair_value,
            "upside_percent": _calculate_return(
                fcf_fair_value,
                current_price,
            ),
            "benchmark": required_fcf_yield,
            "benchmark_label": "5.00% required yield",
            "source": ("Generic conservative FCF-yield assumption"),
            "reliability": 0.30,
            "base_weight": 0.15,
        }

    # ======================================================
    # REQUIRE METHODS
    # ======================================================

    if not methods:
        return {
            "status": "UNAVAILABLE",
            "message": ("Insufficient data for V4 valuation."),
        }

    # ======================================================
    # RELIABILITY-ADJUSTED WEIGHTS
    # ======================================================

    total_raw_weight = 0.0

    for method in methods.values():

        reliability = method.get(
            "reliability",
            0.0,
        )

        base_weight = method.get(
            "base_weight",
            0.0,
        )

        raw_weight = base_weight * reliability

        method["raw_weight"] = raw_weight

        total_raw_weight += raw_weight

    if total_raw_weight <= 0:
        return {
            "status": "UNAVAILABLE",
            "message": ("Valuation method weights unavailable."),
        }

    composite_fair_value = 0.0

    for method in methods.values():

        normalized_weight = method["raw_weight"] / total_raw_weight

        method["weight"] = normalized_weight

        composite_fair_value += method["fair_value"] * normalized_weight

    # ======================================================
    # VALUATION RANGE
    # ======================================================

    fair_values = [
        method["fair_value"] for method in methods.values() if method.get("fair_value") is not None
    ]

    low_value = min(fair_values)
    high_value = max(fair_values)

    # ======================================================
    # COMPOSITE UPSIDE
    # ======================================================

    composite_upside = _calculate_return(
        composite_fair_value,
        current_price,
    )

    status = _valuation_status(composite_upside)

    # ======================================================
    # METHOD AGREEMENT
    # ======================================================

    if composite_fair_value > 0:

        deviations = [
            abs(value - composite_fair_value) / composite_fair_value for value in fair_values
        ]

        average_deviation = sum(deviations) / len(deviations)

    else:
        average_deviation = 1.0

    agreement_score = max(
        0.0,
        1.0 - average_deviation,
    )

    # ======================================================
    # RELIABILITY SCORE
    # ======================================================

    weighted_reliability = sum(
        method["reliability"] * method["weight"] for method in methods.values()
    )

    method_coverage = min(
        len(methods) / 5.0,
        1.0,
    )

    confidence_score = weighted_reliability * 60.0 + agreement_score * 25.0 + method_coverage * 15.0

    # ======================================================
    # BENCHMARK SOURCE CONFIDENCE
    # ======================================================

    peer_relevance_block = benchmarks.get(
        "peer_relevance",
        {},
    )

    if not isinstance(peer_relevance_block, dict):
        peer_relevance_block = {}

    peer_relevance_score = _safe_float(peer_relevance_block.get("score"))

    has_independent_peer_benchmarks = peer_relevance_score is not None

    if not has_independent_peer_benchmarks:
        confidence_score = min(
            confidence_score,
            65.0,
        )

    confidence = _confidence_label(confidence_score)

    # ======================================================
    # MARGIN OF SAFETY
    # ======================================================

    margin_of_safety = (
        ((composite_fair_value - current_price) / composite_fair_value) * 100.0
        if composite_fair_value > 0
        else None
    )

    # ======================================================
    # INTERPRETATION
    # ======================================================

    if composite_upside is None:

        interpretation = "Composite valuation could not be interpreted."

    elif composite_upside >= 15:

        interpretation = (
            "The multi-method valuation indicates meaningful "
            "upside relative to the current market price."
        )

    elif composite_upside >= 5:

        interpretation = (
            "The multi-method valuation indicates modest "
            "upside relative to the current market price."
        )

    elif composite_upside > -5:

        interpretation = (
            "The current market price is broadly aligned "
            "with the multi-method fair-value estimate."
        )

    elif composite_upside > -15:

        interpretation = (
            "The current market price is moderately above " "the multi-method fair-value estimate."
        )

    else:

        interpretation = (
            "The current market price is materially above " "the multi-method fair-value estimate."
        )

    # ======================================================
    # CLEAN OUTPUT
    # ======================================================

    clean_methods = {}

    for key, method in methods.items():

        clean_methods[key] = {
            "name": method["name"],
            "fair_value": round(
                method["fair_value"],
                2,
            ),
            "upside_percent": (
                round(
                    method["upside_percent"],
                    2,
                )
                if method["upside_percent"] is not None
                else None
            ),
            "benchmark": method["benchmark"],
            "benchmark_label": method["benchmark_label"],
            "source": method["source"],
            "reliability": round(
                method["reliability"],
                3,
            ),
            "weight": round(
                method["weight"],
                4,
            ),
        }

    warnings = list(
        benchmarks.get(
            "warnings",
            [],
        )
    )

    warnings.append(
        "FCF Yield is a simplified valuation signal " "and is not a discounted cash flow model."
    )

    if not has_independent_peer_benchmarks:
        warnings.append(
            "Valuation confidence is capped because "
            "independent peer, sector or historical "
            "benchmark multiples are unavailable."
        )

    return {
        "status": "OK",
        "current_price": round(
            current_price,
            2,
        ),
        "price_source": data.get("price_source", "Unknown"),
        "quote_timestamp": data.get("quote_timestamp"),
        "quote_frequency": data.get("quote_frequency", "unavailable"),
        "is_intraday": bool(data.get("is_intraday", False)),
        "is_tick_live": bool(data.get("is_tick_live", False)),
        "composite_fair_value": round(
            composite_fair_value,
            2,
        ),
        "upside_percent": (
            round(
                composite_upside,
                2,
            )
            if composite_upside is not None
            else None
        ),
        "margin_of_safety": (
            round(
                margin_of_safety,
                2,
            )
            if margin_of_safety is not None
            else None
        ),
        "valuation_status": status,
        "confidence": confidence,
        "confidence_score": round(
            confidence_score,
            1,
        ),
        "method_agreement_score": round(
            agreement_score * 100.0,
            1,
        ),
        "method_count": len(methods),
        "low_value": round(
            low_value,
            2,
        ),
        "high_value": round(
            high_value,
            2,
        ),
        "methods": clean_methods,
        "interpretation": interpretation,
        "benchmark_quality": benchmarks.get(
            "data_quality",
            "UNKNOWN",
        ),
        "warnings": warnings,
    }
