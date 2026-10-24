import math
import statistics

import yfinance as yf


def _safe_float(value):
    """Convert value to a finite float or return None."""
    try:
        value = float(value)

        if math.isnan(value) or math.isinf(value):
            return None

        return value

    except (TypeError, ValueError):
        return None


def _median(values):
    """Return median of valid positive numbers."""
    clean = []

    for value in values:
        number = _safe_float(value)

        if number is not None and number > 0:
            clean.append(number)

    if not clean:
        return None

    return statistics.median(clean)


def _median_any(values):
    """
    Return median of all finite numeric values.

    Negative and zero values are allowed.
    Used for growth and operating metrics.
    """
    clean = []

    for value in values:
        number = _safe_float(value)

        if number is not None:
            clean.append(number)

    if not clean:
        return None

    return statistics.median(clean)


# ==========================================================
# PEER GROUPS
# ==========================================================
#
# First version uses manually defined NSE peer groups.
#
# These are transparent rather than pretending Yahoo
# provides a reliable industry peer universe automatically.
#
# We can later move this into a JSON/config/database layer.
# ==========================================================

PEER_GROUPS = {
    "RELIANCE": [
        "IOC.NS",
        "BPCL.NS",
        "HINDPETRO.NS",
        "ONGC.NS",
        "OIL.NS",
        "GAIL.NS",
    ],
    "TCS": [
        "INFY.NS",
        "HCLTECH.NS",
        "WIPRO.NS",
        "TECHM.NS",
        "LTIM.NS",
    ],
    "INFY": [
        "TCS.NS",
        "HCLTECH.NS",
        "WIPRO.NS",
        "TECHM.NS",
        "LTIM.NS",
    ],
    "HDFCBANK": [
        "ICICIBANK.NS",
        "AXISBANK.NS",
        "KOTAKBANK.NS",
        "SBIN.NS",
        "INDUSINDBK.NS",
    ],
    "ICICIBANK": [
        "HDFCBANK.NS",
        "AXISBANK.NS",
        "KOTAKBANK.NS",
        "SBIN.NS",
        "INDUSINDBK.NS",
    ],
}


def _clean_symbol(symbol):
    symbol = str(symbol or "").strip().upper()

    if symbol.endswith(".NS"):
        symbol = symbol[:-3]

    return symbol


def _fetch_peer_metrics(symbol):
    """
    Fetch valuation and quality metrics for one peer.

    Missing Yahoo Finance values remain None and are
    automatically excluded from peer medians.
    """

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}

        return {
            "symbol": symbol,
            "company": info.get(
                "longName",
                symbol,
            ),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            # ==============================================
            # VALUATION
            # ==============================================
            "pe": _safe_float(info.get("trailingPE")),
            "forward_pe": _safe_float(info.get("forwardPE")),
            "pb": _safe_float(info.get("priceToBook")),
            "ev_ebitda": _safe_float(info.get("enterpriseToEbitda")),
            # ==============================================
            # QUALITY / GROWTH
            # ==============================================
            "roe": _safe_float(info.get("returnOnEquity")),
            "revenue_growth": _safe_float(info.get("revenueGrowth")),
            "earnings_growth": _safe_float(info.get("earningsGrowth")),
            "debt_to_equity": _safe_float(info.get("debtToEquity")),
            "operating_margin": _safe_float(info.get("operatingMargins")),
        }

    except Exception:
        return {
            "symbol": symbol,
            "company": symbol,
            "sector": None,
            "industry": None,
            "pe": None,
            "ev_ebitda": None,
            "roe": None,
            "revenue_growth": None,
            "earnings_growth": None,
            "debt_to_equity": None,
            "operating_margin": None,
        }


def generate_peer_benchmarks(symbol):
    """
    Generate independent peer-median valuation benchmarks.

    Returns medians for:
        - trailing P/E
        - forward P/E
        - P/B
        - EV/EBITDA
    """

    base_symbol = _clean_symbol(symbol)

    peers = PEER_GROUPS.get(
        base_symbol,
        [],
    )

    if not peers:
        return {
            "status": "UNAVAILABLE",
            "symbol": base_symbol,
            "message": ("No peer group is configured for this stock."),
            "peers": [],
        }

    peer_data = []

    for peer in peers:
        metrics = _fetch_peer_metrics(peer)
        peer_data.append(metrics)

    # ======================================================
    # MEDIANS
    # ======================================================

    pe_values = [item.get("pe") for item in peer_data]

    forward_pe_values = [item.get("forward_pe") for item in peer_data]

    pb_values = [item.get("pb") for item in peer_data]

    ev_ebitda_values = [item.get("ev_ebitda") for item in peer_data]

    # ======================================================
    # QUALITY / GROWTH DATA
    # ======================================================

    roe_values = [item.get("roe") for item in peer_data]

    revenue_growth_values = [item.get("revenue_growth") for item in peer_data]

    earnings_growth_values = [item.get("earnings_growth") for item in peer_data]

    debt_to_equity_values = [item.get("debt_to_equity") for item in peer_data]

    operating_margin_values = [item.get("operating_margin") for item in peer_data]

    pe_median = _median(pe_values)

    forward_pe_median = _median(forward_pe_values)

    pb_median = _median(pb_values)

    ev_ebitda_median = _median(ev_ebitda_values)

    # ======================================================
    # QUALITY / GROWTH MEDIANS
    # ======================================================

    roe_median = _median(roe_values)

    revenue_growth_median = _median_any(revenue_growth_values)

    earnings_growth_median = _median_any(earnings_growth_values)

    debt_to_equity_median = _median(debt_to_equity_values)

    operating_margin_median = _median_any(operating_margin_values)

    # ======================================================
    # VALID OBSERVATION COUNTS
    # ======================================================

    def count_valid(values):
        count = 0

        for value in values:
            number = _safe_float(value)

            if number is not None and number > 0:
                count += 1

        return count

    counts = {
        "pe": count_valid(pe_values),
        "forward_pe": count_valid(forward_pe_values),
        "pb": count_valid(pb_values),
        "ev_ebitda": count_valid(ev_ebitda_values),
    }

    # ======================================================
    # RELIABILITY
    # ======================================================
    #
    # Reliability here represents peer-data coverage,
    # not certainty that the peer group is economically
    # perfect.
    #
    # 5+ usable peers -> 0.85
    # 4             -> 0.75
    # 3             -> 0.65
    # 2             -> 0.50
    # 1             -> 0.30
    # ======================================================

    def reliability(count):

        if count >= 5:
            return 0.85

        if count == 4:
            return 0.75

        if count == 3:
            return 0.65

        if count == 2:
            return 0.50

        if count == 1:
            return 0.30

        return 0.0

    # ======================================================
    # DATA QUALITY
    # ======================================================

    usable_methods = sum(
        value is not None
        for value in [
            pe_median,
            forward_pe_median,
            pb_median,
            ev_ebitda_median,
        ]
    )

    if usable_methods == 4:
        quality = "GOOD"

    elif usable_methods >= 2:
        quality = "MODERATE"

    elif usable_methods == 1:
        quality = "WEAK"

    else:
        quality = "INSUFFICIENT"

    # ======================================================
    # RETURN
    # ======================================================

    return {
        "status": "OK",
        "symbol": base_symbol,
        "peer_count": len(peers),
        "peers": peer_data,
        "pe": {
            "multiple": (round(pe_median, 2) if pe_median is not None else None),
            "source": "Peer-group median",
            "observations": counts["pe"],
            "reliability": reliability(counts["pe"]),
        },
        "forward_pe": {
            "multiple": (round(forward_pe_median, 2) if forward_pe_median is not None else None),
            "source": "Peer-group median",
            "observations": counts["forward_pe"],
            "reliability": reliability(counts["forward_pe"]),
        },
        "pb": {
            "multiple": (round(pb_median, 2) if pb_median is not None else None),
            "source": "Peer-group median",
            "observations": counts["pb"],
            "reliability": reliability(counts["pb"]),
        },
        "ev_ebitda": {
            "multiple": (round(ev_ebitda_median, 2) if ev_ebitda_median is not None else None),
            "source": "Peer-group median",
            "observations": counts["ev_ebitda"],
            "reliability": reliability(counts["ev_ebitda"]),
        },
        # ==================================================
        # PEER QUALITY BENCHMARKS
        # ==================================================
        "quality_metrics": {
            "roe": {
                "median": (round(roe_median, 4) if roe_median is not None else None),
                "observations": count_valid(roe_values),
            },
            "revenue_growth": {
                "median": (
                    round(revenue_growth_median, 4) if revenue_growth_median is not None else None
                ),
                "observations": sum(
                    _safe_float(value) is not None for value in revenue_growth_values
                ),
            },
            "earnings_growth": {
                "median": (
                    round(earnings_growth_median, 4) if earnings_growth_median is not None else None
                ),
                "observations": sum(
                    _safe_float(value) is not None for value in earnings_growth_values
                ),
            },
            "debt_to_equity": {
                "median": (
                    round(debt_to_equity_median, 3) if debt_to_equity_median is not None else None
                ),
                "observations": count_valid(debt_to_equity_values),
            },
            "operating_margin": {
                "median": (
                    round(operating_margin_median, 4)
                    if operating_margin_median is not None
                    else None
                ),
                "observations": sum(
                    _safe_float(value) is not None for value in operating_margin_values
                ),
            },
        },
        "available_methods": usable_methods,
        "data_quality": quality,
        "warnings": [
            (
                "Peer benchmarks are based on the configured "
                "comparison group and should be interpreted "
                "in the context of differences in growth, "
                "profitability, leverage and business mix."
            ),
            (
                "Reliance Industries is diversified across "
                "multiple businesses, so an energy-sector "
                "peer group does not fully capture its "
                "consolidated economic structure."
            ),
        ],
    }
