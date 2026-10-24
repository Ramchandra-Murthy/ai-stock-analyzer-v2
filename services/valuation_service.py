import math


def _safe_float(value, default=None):
    """Safely convert a value to a finite float."""
    try:
        if value is None:
            return default
        value = float(value)
        return value if math.isfinite(value) else default
    except (TypeError, ValueError):
        return default


def generate_valuation_analysis(
    data,
    fundamental_score,
    investment_score,
):
    """Generate an earnings-based valuation without fabricating missing evidence."""

    data = data if isinstance(data, dict) else {}

    current_price = _safe_float(data.get("price"))
    eps = _safe_float(data.get("eps"))
    trailing_pe = _safe_float(data.get("pe"))
    forward_pe = _safe_float(data.get("forward_pe"))
    revenue_growth = _safe_float(data.get("revenue_growth"))
    earnings_growth = _safe_float(data.get("earnings_growth"))
    fundamental_score = _safe_float(fundamental_score)
    investment_score = _safe_float(investment_score)

    if current_price is None or current_price <= 0 or eps is None or eps <= 0:
        return {
            "status": "UNAVAILABLE",
            "message": "Insufficient price or earnings data for earnings-based valuation.",
        }

    if fundamental_score is None:
        return {
            "status": "INSUFFICIENT DATA",
            "message": "Fundamental score is unavailable; valuation quality cannot be assessed reliably.",
            "current_price": round(current_price, 2),
            "eps": round(eps, 2),
        }

    pe_candidates = [
        value
        for value in (trailing_pe, forward_pe)
        if value is not None and value > 0 and value <= 1000
    ]

    if pe_candidates:
        base_pe = sum(pe_candidates) / len(pe_candidates)
        pe_source = "available P/E evidence"
    else:
        # Without a market P/E observation, do not invent a reference multiple.
        return {
            "status": "INSUFFICIENT DATA",
            "message": "No valid trailing or forward P/E is available for earnings-based valuation.",
            "current_price": round(current_price, 2),
            "eps": round(eps, 2),
        }

    base_pe = max(8.0, min(base_pe, 35.0))

    if fundamental_score >= 80:
        quality_adjustment = 1.10
    elif fundamental_score >= 70:
        quality_adjustment = 1.05
    elif fundamental_score >= 60:
        quality_adjustment = 1.00
    elif fundamental_score >= 50:
        quality_adjustment = 0.95
    else:
        quality_adjustment = 0.90

    growth_adjustment = 1.00
    if earnings_growth is not None and abs(earnings_growth) <= 10:
        if earnings_growth >= 0.20:
            growth_adjustment += 0.10
        elif earnings_growth >= 0.10:
            growth_adjustment += 0.05
        elif earnings_growth < 0:
            growth_adjustment -= 0.10

    if revenue_growth is not None and abs(revenue_growth) <= 10:
        if revenue_growth >= 0.20:
            growth_adjustment += 0.05
        elif revenue_growth >= 0.10:
            growth_adjustment += 0.025
        elif revenue_growth < 0:
            growth_adjustment -= 0.05

    growth_adjustment = max(0.80, min(growth_adjustment, 1.20))
    fair_pe = max(8.0, min(base_pe * quality_adjustment * growth_adjustment, 35.0))
    fair_value = eps * fair_pe

    if not math.isfinite(fair_value) or fair_value <= 0:
        return {
            "status": "UNAVAILABLE",
            "message": "Unable to produce a finite fair-value estimate.",
            "current_price": round(current_price, 2),
            "eps": round(eps, 2),
        }

    upside_percent = ((fair_value - current_price) / current_price) * 100
    margin_of_safety = ((fair_value - current_price) / fair_value) * 100

    if not math.isfinite(upside_percent) or not math.isfinite(margin_of_safety):
        return {
            "status": "UNAVAILABLE",
            "message": "Valuation percentage calculations are unavailable.",
            "current_price": round(current_price, 2),
            "eps": round(eps, 2),
        }

    if upside_percent >= 20:
        valuation_status = "UNDERVALUED"
    elif upside_percent >= 5:
        valuation_status = "SLIGHTLY UNDERVALUED"
    elif upside_percent > -5:
        valuation_status = "FAIRLY VALUED"
    elif upside_percent > -20:
        valuation_status = "SLIGHTLY OVERVALUED"
    else:
        valuation_status = "OVERVALUED"

    if fundamental_score >= 75 and upside_percent >= 15:
        valuation_conviction = "HIGH"
    elif fundamental_score >= 60 and upside_percent >= 5:
        valuation_conviction = "MODERATE"
    elif abs(upside_percent) < 5:
        valuation_conviction = "NEUTRAL"
    else:
        valuation_conviction = "LOW"

    bear_pe = fair_pe * 0.85
    bull_pe = fair_pe * 1.15
    bear_value = eps * bear_pe
    bull_value = eps * bull_pe

    reasons = [
        f"EPS used for valuation: {eps:.2f}.",
        f"Base P/E reference: {base_pe:.2f}x ({pe_source}).",
        f"Quality-adjusted and growth-adjusted fair P/E: {fair_pe:.2f}x.",
        f"Fundamental score: {fundamental_score:.0f}/100.",
    ]

    if earnings_growth is not None and abs(earnings_growth) <= 10:
        reasons.append(f"Earnings growth: {earnings_growth * 100:.2f}%.")
    if revenue_growth is not None and abs(revenue_growth) <= 10:
        reasons.append(f"Revenue growth: {revenue_growth * 100:.2f}%.")

    return {
        "status": "OK",
        "current_price": round(current_price, 2),
        "price_source": data.get("price_source", "Unknown"),
        "quote_timestamp": data.get("quote_timestamp"),
        "quote_frequency": data.get("quote_frequency", "unavailable"),
        "is_intraday": bool(data.get("is_intraday", False)),
        "is_tick_live": bool(data.get("is_tick_live", False)),
        "eps": round(eps, 2),
        "trailing_pe": (
            round(trailing_pe, 2) if trailing_pe is not None and trailing_pe > 0 else None
        ),
        "forward_pe": round(forward_pe, 2) if forward_pe is not None and forward_pe > 0 else None,
        "base_pe": round(base_pe, 2),
        "fair_pe": round(fair_pe, 2),
        "fair_value": round(fair_value, 2),
        "bear_value": round(bear_value, 2),
        "bull_value": round(bull_value, 2),
        "upside_percent": round(upside_percent, 2),
        "margin_of_safety": round(margin_of_safety, 2),
        "valuation_status": valuation_status,
        "valuation_conviction": valuation_conviction,
        "fundamental_score": round(fundamental_score),
        "investment_score": round(investment_score) if investment_score is not None else None,
        "reasons": reasons,
    }
