import math


def _safe_float(value, default=None):
    """Safely convert a value to a finite float."""
    try:
        if value is None:
            return default
        number = float(value)
        return number if math.isfinite(number) else default
    except (TypeError, ValueError):
        return default


def _clean_reasons(reasons):
    """Return a clean list of non-empty reason strings."""
    if not isinstance(reasons, (list, tuple)):
        return []
    return [str(reason).strip() for reason in reasons if reason is not None and str(reason).strip()]


def generate_investment_thesis(
    data,
    investment_score,
    technical_score,
    fundamental_score,
    ai_result,
    score_breakdown,
    technical_reasons,
    fundamental_reasons,
    trade_plan=None,
):
    """Generate an analyst-style thesis without manufacturing missing evidence."""

    data = data if isinstance(data, dict) else {}
    ai_result = ai_result if isinstance(ai_result, dict) else {}
    score_breakdown = score_breakdown if isinstance(score_breakdown, dict) else {}
    trade_plan = trade_plan if isinstance(trade_plan, dict) else {}

    technical_reasons = _clean_reasons(technical_reasons)
    fundamental_reasons = _clean_reasons(fundamental_reasons)

    investment_score = _safe_float(investment_score)
    technical_score = _safe_float(technical_score)
    fundamental_score = _safe_float(fundamental_score)
    ai_score = _safe_float(ai_result.get("score"))

    if investment_score is None:
        return {
            "company": data.get("company", "The company"),
            "sector": data.get("sector", "N/A"),
            "industry": data.get("industry", "N/A"),
            "investment_score": None,
            "conviction": "UNAVAILABLE",
            "thesis": "Investment thesis unavailable because the Investment Score was not produced.",
            "strengths": [],
            "concerns": ["Upstream scoring data is unavailable."],
            "catalysts": [],
            "bull_case": None,
            "base_case": None,
            "bear_case": None,
            "current_price": None,
            "target_price": None,
            "stop_loss": None,
        }

    if technical_score is None or fundamental_score is None:
        return {
            "status": "INSUFFICIENT DATA",
            "message": "Technical and Fundamental evidence are required for a reliable investment thesis.",
            "investment_score": investment_score,
            "technical_score": technical_score,
            "fundamental_score": fundamental_score,
            "ai_score": ai_score,
            "current_price": None,
            "target_price": None,
            "recommendation": "INSUFFICIENT DATA",
            "confidence": 0,
        }

    stability_score = _safe_float(score_breakdown.get("Stability"))

    company = data.get("company", "The company")
    sector = data.get("sector", "N/A")
    industry = data.get("industry", "N/A")

    if investment_score >= 80:
        thesis = (
            f"{company} currently presents a strong investment profile. "
            "The combined available analytical evidence is favorable."
        )
    elif investment_score >= 65:
        thesis = (
            f"{company} currently presents a moderately attractive investment profile. "
            "Several available analytical factors are supportive, while risks remain."
        )
    elif investment_score >= 50:
        thesis = (
            f"{company} currently presents a mixed investment profile. "
            "Available evidence provides support, but conviction is limited."
        )
    elif investment_score >= 35:
        thesis = (
            f"{company} currently presents a cautious investment profile. "
            "The available analytical evidence identifies material weaknesses."
        )
    else:
        thesis = (
            f"{company} currently presents a weak investment profile under "
            "the existing analytical framework."
        )

    strengths = []
    if fundamental_score >= 70:
        strengths.append(f"Fundamental score is strong at {fundamental_score:.0f}/100.")
    if technical_score >= 70:
        strengths.append(f"Technical score is strong at {technical_score:.0f}/100.")
    if ai_score is not None and ai_score >= 70:
        strengths.append(f"AI model score is supportive at {ai_score:.0f}/100.")
    if stability_score is not None and stability_score >= 70:
        strengths.append(f"Stability score is strong at {stability_score:.0f}/100.")

    revenue_growth = _safe_float(data.get("revenue_growth"))
    if revenue_growth is not None and abs(revenue_growth) <= 10 and revenue_growth > 0.10:
        strengths.append(f"Revenue growth is positive at {revenue_growth * 100:.2f}%.")

    operating_cash_flow = _safe_float(data.get("operating_cash_flow"))
    if operating_cash_flow is not None and operating_cash_flow > 0:
        strengths.append("Operating cash flow is positive.")

    free_cash_flow = _safe_float(data.get("free_cash_flow"))
    if free_cash_flow is not None and free_cash_flow > 0:
        strengths.append("Free cash flow is positive.")

    for reason in fundamental_reasons:
        lower_reason = reason.lower()
        if any(
            term in lower_reason
            for term in ["reasonable", "strong", "positive", "manageable", "adequate", "covers"]
        ):
            if reason not in strengths:
                strengths.append(reason)

    concerns = []
    if technical_score < 50:
        concerns.append(f"Technical score is weak at {technical_score:.0f}/100.")
    if fundamental_score < 50:
        concerns.append(f"Fundamental score is weak at {fundamental_score:.0f}/100.")
    if ai_score is not None and ai_score < 50:
        concerns.append(f"AI model score is weak at {ai_score:.0f}/100.")

    earnings_growth = _safe_float(data.get("earnings_growth"))
    if earnings_growth is not None and abs(earnings_growth) <= 10 and earnings_growth < 0:
        concerns.append(f"Earnings growth is negative at {earnings_growth * 100:.2f}%.")

    for reason in technical_reasons:
        lower_reason = reason.lower()
        if any(
            term in lower_reason for term in ["weak", "bearish", "below", "negative", "resistance"]
        ):
            if reason not in concerns:
                concerns.append(reason)

    catalysts = []
    if revenue_growth is not None and abs(revenue_growth) <= 10 and revenue_growth > 0.15:
        catalysts.append(
            "Continued strong revenue growth could improve future earnings performance."
        )
    if earnings_growth is not None and abs(earnings_growth) <= 10 and earnings_growth < 0:
        catalysts.append(
            "A recovery in earnings growth could materially improve the investment outlook."
        )
    if technical_score < 50:
        catalysts.append(
            "Improvement in technical momentum and trend confirmation could strengthen the setup."
        )
    if fundamental_score >= 70:
        catalysts.append("Sustained fundamental performance could support longer-term valuation.")

    current_price = _safe_float(trade_plan.get("current_price"))
    target_price = _safe_float(trade_plan.get("target_price"))
    stop_loss = _safe_float(trade_plan.get("stop_loss"))

    if current_price is not None and current_price <= 0:
        current_price = None
    if target_price is not None and target_price <= 0:
        target_price = None
    if stop_loss is not None and stop_loss <= 0:
        stop_loss = None

    if target_price is not None:
        bull_case = (
            "Improving technical momentum combined with sustained fundamental performance "
            f"could support movement toward the model target of ₹{target_price:,.2f}."
        )
    else:
        bull_case = "Improving earnings, stronger technical momentum and continued fundamental strength could improve the outcome."

    base_case = (
        f"The base case assumes that {company} continues to reflect its current analytical profile, "
        f"with an Investment Score of {investment_score:.0f}/100, Fundamental Score of {fundamental_score:.0f}/100 "
        f"and Technical Score of {technical_score:.0f}/100."
    )

    if stop_loss is not None:
        bear_case = (
            "Further deterioration in technical conditions or fundamental performance could increase downside risk. "
            f"The current trade plan identifies ₹{stop_loss:,.2f} as the stop-loss reference level."
        )
    else:
        bear_case = "Weakening fundamentals, deteriorating earnings or continued bearish technical conditions could increase downside risk."

    if investment_score >= 80:
        conviction = "HIGH"
    elif investment_score >= 65:
        conviction = "MODERATE-HIGH"
    elif investment_score >= 50:
        conviction = "MODERATE"
    elif investment_score >= 35:
        conviction = "LOW"
    else:
        conviction = "VERY LOW"

    return {
        "company": company,
        "sector": sector,
        "industry": industry,
        "investment_score": round(investment_score),
        "conviction": conviction,
        "thesis": thesis,
        "strengths": strengths[:8],
        "concerns": concerns[:8],
        "catalysts": catalysts[:6],
        "bull_case": bull_case,
        "base_case": base_case,
        "bear_case": bear_case,
        "current_price": current_price,
        "target_price": target_price,
        "stop_loss": stop_loss,
    }
