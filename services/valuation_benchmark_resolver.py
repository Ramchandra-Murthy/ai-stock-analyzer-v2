import math


def _safe_float(value):
    """Convert value to a finite float or return None."""
    try:
        value = float(value)

        if math.isnan(value) or math.isinf(value):
            return None

        return value

    except (TypeError, ValueError):
        return None


def _valid_multiple(block):
    """Return a positive benchmark multiple or None."""
    if not isinstance(block, dict):
        return None

    value = _safe_float(block.get("multiple"))

    if value is None or value <= 0:
        return None

    return value


def _safe_reliability(block):
    """Return reliability restricted to 0-1."""
    if not isinstance(block, dict):
        return 0.0

    value = _safe_float(block.get("reliability"))

    if value is None:
        return 0.0

    return max(0.0, min(value, 1.0))


def resolve_valuation_benchmarks(
    company_benchmarks,
    peer_benchmarks=None,
):
    """
    Benchmark Resolver V4.1.

    Priority:
        1. Peer benchmark when sufficiently reliable
        2. Company-derived benchmark as fallback
        3. Method unavailable

    The resolver preserves both benchmark values so the
    valuation report remains transparent.

    IMPORTANT:
    Peer benchmarks are not automatically assumed to be
    economically perfect simply because coverage is high.
    """

    company_benchmarks = company_benchmarks if isinstance(company_benchmarks, dict) else {}

    peer_benchmarks = peer_benchmarks if isinstance(peer_benchmarks, dict) else {}

    methods = [
        "pe",
        "forward_pe",
        "pb",
        "ev_ebitda",
    ]

    resolved = {}

    peer_status_ok = peer_benchmarks.get("status") == "OK"

    company_status_ok = company_benchmarks.get("status") == "OK"

    for method in methods:

        company_block = company_benchmarks.get(method, {}) if company_status_ok else {}

        peer_block = peer_benchmarks.get(method, {}) if peer_status_ok else {}

        company_multiple = _valid_multiple(company_block)

        peer_multiple = _valid_multiple(peer_block)

        company_reliability = _safe_reliability(company_block)

        peer_reliability = _safe_reliability(peer_block)

        observations = peer_block.get(
            "observations",
            0,
        )

        try:
            observations = int(observations)
        except (TypeError, ValueError):
            observations = 0

        # ==================================================
        # SELECT BENCHMARK
        # ==================================================

        if peer_multiple is not None and peer_reliability >= 0.65 and observations >= 3:
            selected_multiple = peer_multiple
            selected_source = peer_block.get(
                "source",
                "Peer-group median",
            )

            selected_reliability = peer_reliability

            selection_type = "PEER"

        elif company_multiple is not None:

            selected_multiple = company_multiple

            selected_source = company_block.get(
                "source",
                "Company-derived benchmark",
            )

            selected_reliability = company_reliability

            selection_type = "COMPANY_FALLBACK"

        else:

            selected_multiple = None
            selected_source = "Unavailable"
            selected_reliability = 0.0
            selection_type = "UNAVAILABLE"

        # ==================================================
        # PEER / COMPANY PREMIUM
        # ==================================================

        premium_discount = None

        if peer_multiple is not None and company_multiple is not None and peer_multiple > 0:
            premium_discount = ((company_multiple / peer_multiple) - 1.0) * 100.0

        resolved[method] = {
            "multiple": selected_multiple,
            "source": selected_source,
            "reliability": selected_reliability,
            "selection_type": selection_type,
            "peer_multiple": peer_multiple,
            "peer_reliability": peer_reliability,
            "peer_observations": observations,
            "company_multiple": company_multiple,
            "company_reliability": (company_reliability),
            "company_premium_to_peer_percent": (
                round(premium_discount, 2) if premium_discount is not None else None
            ),
        }

    # ======================================================
    # COVERAGE
    # ======================================================

    available_methods = sum(item.get("multiple") is not None for item in resolved.values())

    peer_selected_methods = sum(item.get("selection_type") == "PEER" for item in resolved.values())

    fallback_methods = sum(
        item.get("selection_type") == "COMPANY_FALLBACK" for item in resolved.values()
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

    warnings = []

    warnings.extend(
        company_benchmarks.get(
            "warnings",
            [],
        )
    )

    warnings.extend(
        peer_benchmarks.get(
            "warnings",
            [],
        )
    )

    if peer_selected_methods:

        warnings.append(
            f"Independent peer benchmarks were selected "
            f"for {peer_selected_methods} valuation "
            f"method(s)."
        )

    if fallback_methods:

        warnings.append(
            f"Company-derived fallback benchmarks were "
            f"used for {fallback_methods} valuation "
            f"method(s)."
        )

    warnings.append(
        "Peer-multiple valuation does not automatically "
        "adjust for differences in business mix, growth, "
        "profitability, leverage or capital intensity."
    )

    # Remove duplicate warning strings while preserving order.

    unique_warnings = []

    for warning in warnings:
        if warning not in unique_warnings:
            unique_warnings.append(warning)

    return {
        "status": ("OK" if available_methods > 0 else "UNAVAILABLE"),
        "pe": resolved["pe"],
        "forward_pe": resolved["forward_pe"],
        "pb": resolved["pb"],
        "ev_ebitda": resolved["ev_ebitda"],
        "available_methods": available_methods,
        "peer_selected_methods": (peer_selected_methods),
        "company_fallback_methods": (fallback_methods),
        "data_quality": data_quality,
        "warnings": unique_warnings,
    }
