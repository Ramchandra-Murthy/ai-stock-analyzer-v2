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


def _clean_text(value):
    """
    Normalize text for classification comparisons.
    """
    if value is None:
        return ""

    return str(value).strip().lower()


def _clamp(value, minimum, maximum):
    """
    Restrict value to the supplied range.
    """
    return max(
        minimum,
        min(value, maximum),
    )


def calculate_classification_relevance(
    company_sector,
    company_industry,
    peer_sector,
    peer_industry,
):
    """
    Measure basic classification similarity between
    a company and a peer.

    Sector match:
        contributes 0.30

    Industry match:
        contributes 0.40

    Maximum classification score:
        0.70

    Classification alone can therefore never establish
    full economic comparability.
    """

    company_sector = _clean_text(company_sector)
    company_industry = _clean_text(company_industry)

    peer_sector = _clean_text(peer_sector)
    peer_industry = _clean_text(peer_industry)

    sector_match = bool(company_sector) and bool(peer_sector) and company_sector == peer_sector

    industry_match = (
        bool(company_industry) and bool(peer_industry) and company_industry == peer_industry
    )

    score = 0.0

    if sector_match:
        score += 0.30

    if industry_match:
        score += 0.40

    score = _clamp(
        score,
        0.0,
        0.70,
    )

    if score >= 0.70:
        classification_view = "STRONG MATCH"

    elif score >= 0.40:
        classification_view = "MODERATE MATCH"

    elif score > 0:
        classification_view = "WEAK MATCH"

    else:
        classification_view = "NO MATCH"

    return {
        "score": round(score, 4),
        "score_percent": round(score * 100.0, 1),
        "sector_match": sector_match,
        "industry_match": industry_match,
        "classification_view": classification_view,
    }


def _relative_similarity(
    company_value,
    peer_value,
):
    """
    Measure similarity between two positive financial metrics.

    Returns:
        1.0 -> identical
        0.0 -> extremely dissimilar

    Intended for metrics where relative differences are
    economically meaningful, such as ROE and leverage.
    """

    company_value = _safe_float(company_value)
    peer_value = _safe_float(peer_value)

    if company_value is None or peer_value is None or company_value < 0 or peer_value < 0:
        return None

    denominator = max(
        abs(company_value),
        abs(peer_value),
        0.0001,
    )

    difference = abs(company_value - peer_value)

    similarity = 1.0 - (difference / denominator)

    return _clamp(
        similarity,
        0.0,
        1.0,
    )


def _growth_similarity(
    company_growth,
    peer_growth,
):
    """
    Measure similarity between two growth rates.

    Handles:
        positive growth
        zero growth
        negative growth
        opposite growth directions

    Returns:
        1.0 -> identical growth
        0.0 -> highly dissimilar growth
    """

    company_growth = _safe_float(company_growth)

    peer_growth = _safe_float(peer_growth)

    if company_growth is None or peer_growth is None:
        return None

    # ------------------------------------------------------
    # Absolute growth-rate difference
    # ------------------------------------------------------

    difference = abs(company_growth - peer_growth)

    # ------------------------------------------------------
    # Convert difference into similarity.
    #
    # 0 percentage-point difference -> 100% similarity
    # 25 percentage-point difference -> 75%
    # 50 percentage-point difference -> 50%
    # 100+ percentage-point difference -> 0%
    #
    # This avoids unstable relative division around zero.
    # ------------------------------------------------------

    similarity = 1.0 - difference

    similarity = _clamp(
        similarity,
        0.0,
        1.0,
    )

    # ------------------------------------------------------
    # Direction penalty
    # ------------------------------------------------------
    #
    # If one company is growing and the other shrinking,
    # reduce similarity further.
    # ------------------------------------------------------

    opposite_direction = (company_growth > 0 and peer_growth < 0) or (
        company_growth < 0 and peer_growth > 0
    )

    if opposite_direction:
        similarity *= 0.75

    return _clamp(
        similarity,
        0.0,
        1.0,
    )


def calculate_financial_profile_relevance(
    company_metrics,
    peer_metrics,
):
    """
    Measure financial-profile similarity between a company
    and a peer or peer-median profile.

    Factors:
        ROE               25%
        Revenue Growth    20%
        Earnings Growth   15%
        Operating Margin  25%
        Debt / Equity     15%

    Missing factors are excluded and remaining weights are
    renormalized.
    """

    company_metrics = company_metrics if isinstance(company_metrics, dict) else {}

    peer_metrics = peer_metrics if isinstance(peer_metrics, dict) else {}

    # ======================================================
    # NORMALIZE DEBT / EQUITY
    # ======================================================

    def normalize_debt_to_equity(value):
        value = _safe_float(value)

        if value is None:
            return None

        # Yahoo commonly returns debtToEquity as percentage.
        # Example:
        # 36.653 -> 0.36653x
        if abs(value) > 10:
            return value / 100.0

        return value

    # ======================================================
    # INDIVIDUAL SIMILARITIES
    # ======================================================

    roe_similarity = _relative_similarity(
        company_metrics.get("roe"),
        peer_metrics.get("roe"),
    )

    revenue_similarity = _growth_similarity(
        company_metrics.get("revenue_growth"),
        peer_metrics.get("revenue_growth"),
    )

    earnings_similarity = _growth_similarity(
        company_metrics.get("earnings_growth"),
        peer_metrics.get("earnings_growth"),
    )

    margin_similarity = _relative_similarity(
        company_metrics.get("operating_margin"),
        peer_metrics.get("operating_margin"),
    )

    company_de = normalize_debt_to_equity(company_metrics.get("debt_to_equity"))

    peer_de = normalize_debt_to_equity(peer_metrics.get("debt_to_equity"))

    leverage_similarity = _relative_similarity(
        company_de,
        peer_de,
    )

    # ======================================================
    # WEIGHTS
    # ======================================================

    weights = {
        "roe": 0.25,
        "revenue_growth": 0.20,
        "earnings_growth": 0.15,
        "operating_margin": 0.25,
        "debt_to_equity": 0.15,
    }

    similarities = {
        "roe": roe_similarity,
        "revenue_growth": revenue_similarity,
        "earnings_growth": earnings_similarity,
        "operating_margin": margin_similarity,
        "debt_to_equity": leverage_similarity,
    }

    # ======================================================
    # WEIGHTED SCORE
    # ======================================================

    weighted_score = 0.0
    active_weight = 0.0

    for name, similarity in similarities.items():

        if similarity is None:
            continue

        weight = weights[name]

        weighted_score += similarity * weight

        active_weight += weight

    if active_weight > 0:
        score = weighted_score / active_weight
    else:
        score = 0.0

    score = _clamp(
        score,
        0.0,
        1.0,
    )

    # ======================================================
    # INTERPRETATION
    # ======================================================

    if score >= 0.80:
        view = "VERY STRONG"

    elif score >= 0.65:
        view = "STRONG"

    elif score >= 0.50:
        view = "MODERATE"

    elif score >= 0.35:
        view = "WEAK"

    else:
        view = "VERY WEAK"

    return {
        "score": round(score, 4),
        "score_percent": round(
            score * 100.0,
            1,
        ),
        "view": view,
        "active_weight": round(
            active_weight,
            4,
        ),
        "similarities": {
            name: (round(value, 4) if value is not None else None)
            for name, value in similarities.items()
        },
        "weights": weights,
        "normalized_debt_to_equity": {
            "company": company_de,
            "peer": peer_de,
        },
    }


# ==========================================================
# BUSINESS MODEL PROFILES
# ==========================================================
#
# These profiles describe how well a conventional sector
# peer group represents the consolidated business.
#
# The score is NOT company quality.
# It measures suitability of the configured peer group for
# consolidated relative valuation.
#
# 1.00 -> peer group closely represents the business
# 0.00 -> peer group is economically inappropriate
# ==========================================================

BUSINESS_MODEL_PROFILES = {
    "RELIANCE": {
        "score": 0.40,
        "profile": "HIGHLY DIVERSIFIED",
        "reason": (
            "Reliance Industries has material businesses "
            "outside the conventional oil and gas peer set, "
            "including telecom/digital and retail operations. "
            "The configured energy peer group therefore "
            "represents only part of the consolidated business."
        ),
    },
    "TCS": {
        "score": 0.90,
        "profile": "FOCUSED",
        "reason": (
            "TCS is primarily an IT services company and its "
            "configured large-cap IT peer group provides a "
            "relatively close business-model comparison."
        ),
    },
    "INFY": {
        "score": 0.90,
        "profile": "FOCUSED",
        "reason": (
            "Infosys is primarily an IT services company and "
            "its configured IT peer group provides a relatively "
            "close business-model comparison."
        ),
    },
    "HDFCBANK": {
        "score": 0.90,
        "profile": "FOCUSED",
        "reason": (
            "HDFC Bank is predominantly a banking business and "
            "the configured banking peer group provides a "
            "relatively close economic comparison."
        ),
    },
    "ICICIBANK": {
        "score": 0.90,
        "profile": "FOCUSED",
        "reason": (
            "ICICI Bank is predominantly a banking business and "
            "the configured banking peer group provides a "
            "relatively close economic comparison."
        ),
    },
}


def _clean_symbol(symbol):
    """
    Normalize NSE symbols for profile lookup.

    Examples:
        RELIANCE    -> RELIANCE
        RELIANCE.NS -> RELIANCE
    """

    symbol = str(symbol or "").strip().upper()

    if symbol.endswith(".NS"):
        symbol = symbol[:-3]

    return symbol


def calculate_business_model_relevance(symbol):
    """
    Return business-model relevance for the configured
    peer universe.

    This measures peer suitability, not company quality.
    """

    symbol = _clean_symbol(symbol)

    profile = BUSINESS_MODEL_PROFILES.get(symbol)

    if profile is None:
        return {
            "score": 0.50,
            "score_percent": 50.0,
            "profile": "UNASSESSED",
            "reason": (
                "No explicit business-model relevance profile "
                "is configured for this company. A neutral "
                "default is used until peer suitability is "
                "reviewed."
            ),
            "configured": False,
        }

    score = _safe_float(profile.get("score"))

    if score is None:
        score = 0.50

    score = _clamp(
        score,
        0.0,
        1.0,
    )

    return {
        "score": round(score, 4),
        "score_percent": round(
            score * 100.0,
            1,
        ),
        "profile": profile.get(
            "profile",
            "UNASSESSED",
        ),
        "reason": profile.get(
            "reason",
            "",
        ),
        "configured": True,
    }


def calculate_peer_relevance(
    classification_result,
    financial_result,
    business_model_result,
):
    """
    Calculate final peer relevance.

    Components:
        Classification similarity     25%
        Financial-profile similarity  30%
        Business-model relevance      45%

    Business-model relevance receives the largest weight
    because matching sector/industry labels do not by
    themselves establish economic comparability.
    """

    classification_result = classification_result if isinstance(classification_result, dict) else {}

    financial_result = financial_result if isinstance(financial_result, dict) else {}

    business_model_result = business_model_result if isinstance(business_model_result, dict) else {}

    classification_score = _safe_float(classification_result.get("score"))

    financial_score = _safe_float(financial_result.get("score"))

    business_model_score = _safe_float(business_model_result.get("score"))

    components = {
        "classification": classification_score,
        "financial_profile": financial_score,
        "business_model": business_model_score,
    }

    weights = {
        "classification": 0.25,
        "financial_profile": 0.30,
        "business_model": 0.45,
    }

    weighted_score = 0.0
    active_weight = 0.0

    for name, score in components.items():

        if score is None:
            continue

        score = _clamp(
            score,
            0.0,
            1.0,
        )

        weight = weights[name]

        weighted_score += score * weight
        active_weight += weight

    if active_weight > 0:
        relevance_score = weighted_score / active_weight
    else:
        relevance_score = 0.0

    relevance_score = _clamp(
        relevance_score,
        0.0,
        1.0,
    )

    # ======================================================
    # RELEVANCE CLASSIFICATION
    # ======================================================

    if relevance_score >= 0.80:
        relevance_view = "VERY HIGH"

    elif relevance_score >= 0.65:
        relevance_view = "HIGH"

    elif relevance_score >= 0.50:
        relevance_view = "MODERATE"

    elif relevance_score >= 0.35:
        relevance_view = "LOW"

    else:
        relevance_view = "VERY LOW"

    return {
        "status": "OK",
        "score": round(
            relevance_score,
            4,
        ),
        "score_percent": round(
            relevance_score * 100.0,
            1,
        ),
        "relevance_view": relevance_view,
        "active_weight": round(
            active_weight,
            4,
        ),
        "components": {
            "classification": classification_result,
            "financial_profile": financial_result,
            "business_model": business_model_result,
        },
        "weights": weights,
    }


def apply_peer_relevance_to_benchmarks(
    benchmarks,
    relevance_result,
):
    """
    Adjust benchmark reliability according to economic
    peer relevance.

    IMPORTANT:
    Peer multiples themselves are NOT modified here.

    Quality adjustment answers:
        What multiple might this company deserve relative
        to the peer median?

    Peer relevance answers:
        How much confidence should we place in that peer
        multiple for this company?

    A 50% floor prevents imperfect peer relevance from
    completely eliminating otherwise useful relative
    valuation evidence.
    """

    benchmarks = benchmarks if isinstance(benchmarks, dict) else {}

    relevance_result = relevance_result if isinstance(relevance_result, dict) else {}

    relevance_score = _safe_float(relevance_result.get("score"))

    if relevance_score is None:
        relevance_score = 0.50

    relevance_score = _clamp(
        relevance_score,
        0.0,
        1.0,
    )

    # ======================================================
    # RELEVANCE MULTIPLIER
    # ======================================================

    relevance_multiplier = 0.50 + (0.50 * relevance_score)

    methods = [
        "pe",
        "forward_pe",
        "pb",
        "ev_ebitda",
    ]

    adjusted = {}

    for method in methods:

        original = benchmarks.get(
            method,
            {},
        )

        if not isinstance(original, dict):
            original = {}

        block = dict(original)

        original_reliability = _safe_float(original.get("reliability"))

        if original_reliability is None:
            adjusted_reliability = None

        else:
            adjusted_reliability = original_reliability * relevance_multiplier

            adjusted_reliability = _clamp(
                adjusted_reliability,
                0.0,
                1.0,
            )

        block["pre_relevance_reliability"] = original_reliability

        block["peer_relevance_score"] = relevance_score

        block["peer_relevance_multiplier"] = relevance_multiplier

        block["reliability"] = (
            round(adjusted_reliability, 4) if adjusted_reliability is not None else None
        )

        adjusted[method] = block

    result = dict(benchmarks)

    for method in methods:
        result[method] = adjusted[method]

    result["peer_relevance"] = {
        "score": round(
            relevance_score,
            4,
        ),
        "score_percent": round(
            relevance_score * 100.0,
            1,
        ),
        "view": relevance_result.get(
            "relevance_view",
            "UNKNOWN",
        ),
        "reliability_multiplier": round(
            relevance_multiplier,
            4,
        ),
    }

    return result


def generate_peer_relevance(
    symbol,
    company_data,
    peer_benchmarks,
):
    """
    Generate the complete V4.3 peer-relevance assessment.

    Pipeline:
        Company classification
        -> peer classification
        -> classification relevance

        Company financial profile
        -> peer median financial profile
        -> financial-profile relevance

        Symbol
        -> business-model relevance

        All components
        -> final peer relevance
    """

    company_data = company_data if isinstance(company_data, dict) else {}

    peer_benchmarks = peer_benchmarks if isinstance(peer_benchmarks, dict) else {}

    # ======================================================
    # CLASSIFICATION
    # ======================================================

    company_sector = company_data.get("sector")
    company_industry = company_data.get("industry")

    peers = peer_benchmarks.get("peers", [])

    if not isinstance(peers, list):
        peers = []

    peer_sectors = []
    peer_industries = []

    for peer in peers:

        if not isinstance(peer, dict):
            continue

        sector = peer.get("sector")
        industry = peer.get("industry")

        if sector:
            peer_sectors.append(_clean_text(sector))

        if industry:
            peer_industries.append(_clean_text(industry))

    # ------------------------------------------------------
    # Determine representative peer classification.
    # ------------------------------------------------------

    def most_common(values):

        if not values:
            return ""

        counts = {}

        for value in values:
            counts[value] = counts.get(value, 0) + 1

        return max(
            counts,
            key=counts.get,
        )

    peer_sector = most_common(peer_sectors)

    peer_industry = most_common(peer_industries)

    classification = calculate_classification_relevance(
        company_sector,
        company_industry,
        peer_sector,
        peer_industry,
    )

    # ======================================================
    # FINANCIAL PROFILE
    # ======================================================

    quality_metrics = peer_benchmarks.get(
        "quality_metrics",
        {},
    )

    def peer_median(name):

        block = quality_metrics.get(
            name,
            {},
        )

        if not isinstance(block, dict):
            return None

        return block.get("median")

    peer_financial_profile = {
        "roe": peer_median("roe"),
        "revenue_growth": peer_median("revenue_growth"),
        "earnings_growth": peer_median("earnings_growth"),
        "operating_margin": peer_median("operating_margin"),
        "debt_to_equity": peer_median("debt_to_equity"),
    }

    financial = calculate_financial_profile_relevance(
        company_data,
        peer_financial_profile,
    )

    # ======================================================
    # BUSINESS MODEL
    # ======================================================

    business_model = calculate_business_model_relevance(symbol)

    # ======================================================
    # FINAL RELEVANCE
    # ======================================================

    result = calculate_peer_relevance(
        classification,
        financial,
        business_model,
    )

    result["symbol"] = _clean_symbol(symbol)

    result["peer_classification"] = {
        "sector": peer_sector,
        "industry": peer_industry,
    }

    result["peer_financial_profile"] = peer_financial_profile

    return result
