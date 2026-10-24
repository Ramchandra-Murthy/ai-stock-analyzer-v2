import math


def _safe_float(value):
    """
    Convert value to a finite float or return None.
    """
    try:
        value = float(value)

        if math.isnan(value) or math.isinf(value):
            return None

        return value

    except (TypeError, ValueError):
        return None


def _clamp(value, minimum, maximum):
    """
    Restrict value to the supplied range.
    """
    return max(
        minimum,
        min(value, maximum),
    )


def _metric_result(
    company_value,
    peer_value,
    adjustment,
    observations,
):
    """
    Standard result structure for one quality factor.
    """
    return {
        "company_value": company_value,
        "peer_median": peer_value,
        "adjustment": adjustment,
        "observations": observations,
    }


def _roe_adjustment(
    company_roe,
    peer_roe,
    observations,
):
    """
    Calculate a profitability adjustment from ROE.

    Adjustment is deliberately capped at +/-10%.

    Higher ROE than peers -> valuation premium.
    Lower ROE than peers  -> valuation discount.
    """

    company_roe = _safe_float(company_roe)
    peer_roe = _safe_float(peer_roe)

    try:
        observations = int(observations)
    except (TypeError, ValueError):
        observations = 0

    # ------------------------------------------------------
    # Missing or insufficient data
    # ------------------------------------------------------

    if company_roe is None or peer_roe is None or peer_roe <= 0 or observations < 3:
        return _metric_result(
            company_roe,
            peer_roe,
            0.0,
            observations,
        )

    # ------------------------------------------------------
    # Relative ROE difference
    # ------------------------------------------------------

    relative_difference = (company_roe / peer_roe) - 1.0

    # ------------------------------------------------------
    # Convert difference into valuation adjustment
    # ------------------------------------------------------
    #
    # Only 20% of the relative ROE advantage/disadvantage
    # is translated into a valuation premium/discount.
    #
    # Example:
    #
    # Company ROE = 15%
    # Peer ROE    = 12%
    #
    # Relative advantage = 25%
    #
    # Adjustment:
    # 25% * 20% = +5%
    #
    # Hard cap = +/-10%
    # ------------------------------------------------------

    adjustment = relative_difference * 0.20

    adjustment = _clamp(
        adjustment,
        -0.10,
        0.10,
    )

    return _metric_result(
        company_roe,
        peer_roe,
        adjustment,
        observations,
    )


def _revenue_growth_adjustment(
    company_growth,
    peer_growth,
    observations,
):
    """
    Calculate valuation adjustment from revenue growth.

    Stronger revenue growth than peers -> premium.
    Weaker revenue growth than peers   -> discount.

    Adjustment is capped at +/-10%.
    """

    company_growth = _safe_float(company_growth)
    peer_growth = _safe_float(peer_growth)

    try:
        observations = int(observations)
    except (TypeError, ValueError):
        observations = 0

    # ------------------------------------------------------
    # Missing or insufficient data
    # ------------------------------------------------------

    if company_growth is None or peer_growth is None or observations < 3:
        return _metric_result(
            company_growth,
            peer_growth,
            0.0,
            observations,
        )

    # ------------------------------------------------------
    # Growth difference
    # ------------------------------------------------------
    #
    # Use the absolute percentage-point difference rather
    # than company_growth / peer_growth.
    #
    # This is safer when peer growth is close to zero or
    # negative.
    # ------------------------------------------------------

    growth_difference = company_growth - peer_growth

    # ------------------------------------------------------
    # Convert growth difference into valuation adjustment
    # ------------------------------------------------------
    #
    # 50% of the growth-rate difference is translated into
    # a valuation adjustment.
    #
    # Example:
    #
    # Company growth = 20%
    # Peer growth    = 10%
    #
    # Difference = +10 percentage points
    #
    # Adjustment = 10% * 50% = +5%
    #
    # Hard cap = +/-10%
    # ------------------------------------------------------

    adjustment = growth_difference * 0.50

    adjustment = _clamp(
        adjustment,
        -0.10,
        0.10,
    )

    return _metric_result(
        company_growth,
        peer_growth,
        adjustment,
        observations,
    )


def _earnings_growth_adjustment(
    company_growth,
    peer_growth,
    observations,
):
    """
    Calculate valuation adjustment from earnings growth.

    Earnings growth is more volatile than revenue growth,
    so its influence is deliberately smaller.

    Adjustment is capped at +/-7.5%.
    """

    company_growth = _safe_float(company_growth)
    peer_growth = _safe_float(peer_growth)

    try:
        observations = int(observations)
    except (TypeError, ValueError):
        observations = 0

    # ------------------------------------------------------
    # Missing or insufficient data
    # ------------------------------------------------------

    if company_growth is None or peer_growth is None or observations < 3:
        return _metric_result(
            company_growth,
            peer_growth,
            0.0,
            observations,
        )

    # ------------------------------------------------------
    # Earnings growth difference
    # ------------------------------------------------------
    #
    # Use percentage-point difference rather than relative
    # division because earnings growth may be negative,
    # zero or unusually large.
    # ------------------------------------------------------

    growth_difference = company_growth - peer_growth

    # ------------------------------------------------------
    # Translate only 15% of the difference into valuation.
    #
    # Earnings growth can be highly cyclical and affected
    # by base effects, so it receives less influence than
    # revenue growth.
    #
    # Hard cap = +/-7.5%
    # ------------------------------------------------------

    adjustment = growth_difference * 0.15

    adjustment = _clamp(
        adjustment,
        -0.075,
        0.075,
    )

    return _metric_result(
        company_growth,
        peer_growth,
        adjustment,
        observations,
    )


def _operating_margin_adjustment(
    company_margin,
    peer_margin,
    observations,
):
    """
    Calculate valuation adjustment from operating margin.

    Higher operating margin than peers -> premium.
    Lower operating margin than peers  -> discount.

    Uses percentage-point difference because margins
    can be zero or negative.

    Adjustment is capped at +/-7.5%.
    """

    company_margin = _safe_float(company_margin)
    peer_margin = _safe_float(peer_margin)

    try:
        observations = int(observations)
    except (TypeError, ValueError):
        observations = 0

    # ------------------------------------------------------
    # Missing or insufficient data
    # ------------------------------------------------------

    if company_margin is None or peer_margin is None or observations < 3:
        return _metric_result(
            company_margin,
            peer_margin,
            0.0,
            observations,
        )

    # ------------------------------------------------------
    # Margin difference
    # ------------------------------------------------------

    margin_difference = company_margin - peer_margin

    # ------------------------------------------------------
    # Convert margin advantage into valuation adjustment.
    #
    # 50% of the percentage-point margin difference is
    # translated into a premium or discount.
    #
    # Example:
    #
    # Company margin = 12%
    # Peer margin    = 8%
    #
    # Difference = +4 percentage points
    #
    # Adjustment = 4% * 50% = +2%
    #
    # Hard cap = +/-7.5%
    # ------------------------------------------------------

    adjustment = margin_difference * 0.50

    adjustment = _clamp(
        adjustment,
        -0.075,
        0.075,
    )

    return _metric_result(
        company_margin,
        peer_margin,
        adjustment,
        observations,
    )


def _normalize_debt_to_equity(value):
    """
    Normalize debt-to-equity into ratio form.

    Examples:
        0.37   -> 0.37x
        56.389 -> 0.56389x

    Yahoo Finance commonly reports debtToEquity in
    percentage-style units, while our research data may
    already store the value as a ratio.
    """

    value = _safe_float(value)

    if value is None:
        return None

    # Values above 10 are assumed to be Yahoo-style
    # percentage representation.
    if abs(value) > 10:
        return value / 100.0

    return value


def _debt_to_equity_adjustment(
    company_de,
    peer_de,
    observations,
):
    """
    Calculate leverage adjustment from debt-to-equity.

    Lower leverage than peers -> premium.
    Higher leverage than peers -> discount.

    Adjustment is capped at +/-7.5%.
    """

    company_de = _normalize_debt_to_equity(company_de)

    peer_de = _normalize_debt_to_equity(peer_de)

    try:
        observations = int(observations)
    except (TypeError, ValueError):
        observations = 0

    # ------------------------------------------------------
    # Missing or insufficient data
    # ------------------------------------------------------

    if company_de is None or peer_de is None or peer_de <= 0 or observations < 3:
        return _metric_result(
            company_de,
            peer_de,
            0.0,
            observations,
        )

    # ------------------------------------------------------
    # Relative leverage difference
    # ------------------------------------------------------
    #
    # Positive value means company leverage is LOWER
    # than peers and therefore receives a premium.
    #
    # Example:
    #
    # Company D/E = 0.40x
    # Peer D/E    = 0.60x
    #
    # Leverage advantage:
    #
    # 1 - (0.40 / 0.60)
    # = 33.3%
    # ------------------------------------------------------

    leverage_advantage = 1.0 - (company_de / peer_de)

    # Translate only 20% of the relative leverage
    # advantage/disadvantage into valuation.

    adjustment = leverage_advantage * 0.20

    adjustment = _clamp(
        adjustment,
        -0.075,
        0.075,
    )

    return _metric_result(
        company_de,
        peer_de,
        adjustment,
        observations,
    )


def calculate_quality_adjustment(
    company_data,
    peer_benchmarks,
):
    """
    Calculate the V4.2 composite quality adjustment.

    Factors:
        ROE              25%
        Revenue Growth   25%
        Earnings Growth  15%
        Operating Margin 20%
        Debt / Equity    15%

    The final adjustment is capped at +/-15%.
    """

    company_data = company_data if isinstance(company_data, dict) else {}

    peer_benchmarks = peer_benchmarks if isinstance(peer_benchmarks, dict) else {}

    quality_metrics = peer_benchmarks.get("quality_metrics", {})

    # ======================================================
    # PEER METRIC BLOCKS
    # ======================================================

    roe_peer = quality_metrics.get("roe", {})

    revenue_peer = quality_metrics.get(
        "revenue_growth",
        {},
    )

    earnings_peer = quality_metrics.get(
        "earnings_growth",
        {},
    )

    margin_peer = quality_metrics.get(
        "operating_margin",
        {},
    )

    debt_peer = quality_metrics.get(
        "debt_to_equity",
        {},
    )

    # ======================================================
    # INDIVIDUAL FACTORS
    # ======================================================

    roe = _roe_adjustment(
        company_data.get("roe"),
        roe_peer.get("median"),
        roe_peer.get("observations", 0),
    )

    revenue_growth = _revenue_growth_adjustment(
        company_data.get("revenue_growth"),
        revenue_peer.get("median"),
        revenue_peer.get("observations", 0),
    )

    earnings_growth = _earnings_growth_adjustment(
        company_data.get("earnings_growth"),
        earnings_peer.get("median"),
        earnings_peer.get("observations", 0),
    )

    operating_margin = _operating_margin_adjustment(
        company_data.get("operating_margin"),
        margin_peer.get("median"),
        margin_peer.get("observations", 0),
    )

    debt_to_equity = _debt_to_equity_adjustment(
        company_data.get("debt_to_equity"),
        debt_peer.get("median"),
        debt_peer.get("observations", 0),
    )

    # ======================================================
    # FACTOR WEIGHTS
    # ======================================================

    weights = {
        "roe": 0.25,
        "revenue_growth": 0.25,
        "earnings_growth": 0.15,
        "operating_margin": 0.20,
        "debt_to_equity": 0.15,
    }

    factors = {
        "roe": roe,
        "revenue_growth": revenue_growth,
        "earnings_growth": earnings_growth,
        "operating_margin": operating_margin,
        "debt_to_equity": debt_to_equity,
    }

    # ======================================================
    # WEIGHTED COMPOSITE
    # ======================================================

    weighted_adjustment = 0.0
    active_weight = 0.0

    for name, result in factors.items():

        observations = result.get(
            "observations",
            0,
        )

        adjustment = _safe_float(result.get("adjustment"))

        # Only include factors with adequate peer coverage.

        if adjustment is not None and observations >= 3:
            weight = weights[name]

            weighted_adjustment += adjustment * weight

            active_weight += weight

    # Renormalize if one or more factors are unavailable.

    if active_weight > 0:
        composite_adjustment = weighted_adjustment / active_weight
    else:
        composite_adjustment = 0.0

    # ======================================================
    # FINAL SAFETY CAP
    # ======================================================

    composite_adjustment = _clamp(
        composite_adjustment,
        -0.15,
        0.15,
    )

    # ======================================================
    # INTERPRETATION
    # ======================================================

    if composite_adjustment >= 0.075:
        quality_view = "STRONG PREMIUM"

    elif composite_adjustment >= 0.025:
        quality_view = "MODERATE PREMIUM"

    elif composite_adjustment > -0.025:
        quality_view = "NEUTRAL"

    elif composite_adjustment > -0.075:
        quality_view = "MODERATE DISCOUNT"

    else:
        quality_view = "STRONG DISCOUNT"

    return {
        "status": "OK",
        "composite_adjustment": round(
            composite_adjustment,
            4,
        ),
        "composite_adjustment_percent": round(
            composite_adjustment * 100.0,
            2,
        ),
        "quality_view": quality_view,
        "active_weight": round(
            active_weight,
            4,
        ),
        "factors": factors,
        "weights": weights,
    }


def apply_quality_adjustment_to_benchmarks(
    peer_benchmarks,
    quality_result,
):
    """
    Apply the V4.2 composite quality adjustment to peer
    valuation multiples.

    Example:
        Peer P/E = 10.00x
        Quality adjustment = +5%

        Adjusted P/E = 10.50x
    """

    peer_benchmarks = peer_benchmarks if isinstance(peer_benchmarks, dict) else {}

    quality_result = quality_result if isinstance(quality_result, dict) else {}

    adjustment = _safe_float(quality_result.get("composite_adjustment"))

    if adjustment is None:
        adjustment = 0.0

    # Additional safety protection.
    adjustment = _clamp(
        adjustment,
        -0.15,
        0.15,
    )

    methods = [
        "pe",
        "forward_pe",
        "pb",
        "ev_ebitda",
    ]

    adjusted = {}

    for method in methods:

        block = peer_benchmarks.get(
            method,
            {},
        )

        if not isinstance(block, dict):
            block = {}

        peer_multiple = _safe_float(block.get("multiple"))

        reliability = _safe_float(block.get("reliability"))

        observations = block.get(
            "observations",
            0,
        )

        try:
            observations = int(observations)
        except (TypeError, ValueError):
            observations = 0

        if peer_multiple is None or peer_multiple <= 0:
            adjusted_multiple = None

        else:
            adjusted_multiple = peer_multiple * (1.0 + adjustment)

        adjusted[method] = {
            "multiple": (round(adjusted_multiple, 2) if adjusted_multiple is not None else None),
            "raw_peer_multiple": peer_multiple,
            "quality_adjustment": adjustment,
            "quality_adjustment_percent": round(
                adjustment * 100.0,
                2,
            ),
            "source": (
                "Quality-adjusted peer median" if adjusted_multiple is not None else "Unavailable"
            ),
            "reliability": reliability,
            "observations": observations,
        }

    return {
        "status": "OK",
        "data_quality": peer_benchmarks.get(
            "data_quality",
            "UNKNOWN",
        ),
        "warnings": list(
            peer_benchmarks.get(
                "warnings",
                [],
            )
        ),
        "quality_adjustment": adjustment,
        "quality_adjustment_percent": round(
            adjustment * 100.0,
            2,
        ),
        "quality_view": quality_result.get(
            "quality_view",
            "N/A",
        ),
        "pe": adjusted["pe"],
        "forward_pe": adjusted["forward_pe"],
        "pb": adjusted["pb"],
        "ev_ebitda": adjusted["ev_ebitda"],
    }
