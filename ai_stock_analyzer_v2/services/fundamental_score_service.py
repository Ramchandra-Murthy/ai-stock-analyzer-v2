import math


def to_float(value):
    """Safely convert a value to a finite float, or return None."""
    if value is None:
        return None
    if isinstance(value, str):
        value = value.replace("%", "").replace(",", "").replace("₹", "").replace("Rs.", "").strip()
        if value.upper() in {"", "N/A", "NA", "NONE", "-"}:
            return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def _percent(value):
    value = to_float(value)
    if value is None or abs(value) > 10:
        return None
    result = value * 100.0
    return result if math.isfinite(result) and abs(result) <= 1000 else None


def _debt_equity_ratio(value):
    value = to_float(value)
    if value is None or value < 0 or value > 10000:
        return None
    return value / 100.0


def _normalize_category(metric_scores, maximum=20):
    if not metric_scores:
        return None
    earned = sum(item[0] for item in metric_scores)
    possible = sum(item[1] for item in metric_scores)
    if possible <= 0:
        return None
    return max(0.0, min((earned / possible) * maximum, maximum))


def _is_bank(data):
    """Identify banks from available Yahoo sector/industry metadata."""
    sector = str(data.get("sector") or "").strip().lower()
    industry = str(data.get("industry") or "").strip().lower()
    text = f"{sector} {industry}"
    return any(
        term in text
        for term in (
            "bank",
            "banks",
            "banking",
            "credit intermediation",
            "commercial lending",
        )
    )


def calculate_fundamental_score(data):
    """Calculate a 0-100 fundamental score, excluding unsuitable bank metrics."""
    if not isinstance(data, dict):
        return None, ["Fundamental data unavailable."]

    reasons = []
    is_bank = _is_bank(data)
    pe, pb = to_float(data.get("pe")), to_float(data.get("pb"))
    if pe is not None and pe <= 0:
        pe = None
    if pb is not None and pb <= 0:
        pb = None

    roe = _percent(data.get("roe"))
    roa = _percent(data.get("roa"))
    profit_margin = _percent(data.get("profit_margin"))
    operating_margin = None if is_bank else _percent(data.get("operating_margin"))
    revenue_growth = _percent(data.get("revenue_growth"))
    earnings_growth = _percent(data.get("earnings_growth"))

    # Valuation: retain P/E and P/B for banks and non-banks.
    metrics = []
    if pe is not None:
        points = 10 if pe <= 15 else 8 if pe <= 25 else 5 if pe <= 35 else 2 if pe <= 50 else 0
        label = (
            "attractive"
            if pe <= 15
            else (
                "reasonable"
                if pe <= 25
                else "moderate" if pe <= 35 else "expensive" if pe <= 50 else "very high"
            )
        )
        reasons.append(f"P/E of {pe:.2f} indicates {label} valuation.")
        metrics.append((points, 10))
    if pb is not None:
        points = 10 if pb <= 1.5 else 8 if pb <= 3 else 5 if pb <= 5 else 2 if pb <= 8 else 0
        reasons.append(f"P/B of {pb:.2f} indicates book-value valuation.")
        metrics.append((points, 10))
    valuation_score = _normalize_category(metrics)

    # Profitability: ROE, ROA and net margin remain available for banks.
    metrics = []
    if roe is not None:
        points = 6 if roe >= 20 else 5 if roe >= 15 else 4 if roe >= 10 else 2 if roe >= 5 else 0
        reasons.append(f"ROE of {roe:.2f}%.")
        metrics.append((points, 6))
    if roa is not None:
        points = 4 if roa >= 10 else 3 if roa >= 5 else 2 if roa >= 2 else 1 if roa > 0 else 0
        reasons.append(f"ROA of {roa:.2f}%.")
        metrics.append((points, 4))
    if profit_margin is not None:
        points = (
            5
            if profit_margin >= 20
            else (
                4
                if profit_margin >= 10
                else 3 if profit_margin >= 5 else 1 if profit_margin > 0 else 0
            )
        )
        reasons.append(f"Net profit margin is {profit_margin:.2f}%.")
        metrics.append((points, 5))
    if operating_margin is not None:
        points = (
            5
            if operating_margin >= 25
            else (
                4
                if operating_margin >= 15
                else 3 if operating_margin >= 10 else 1 if operating_margin > 0 else 0
            )
        )
        reasons.append(f"Operating margin is {operating_margin:.2f}%.")
        metrics.append((points, 5))
    profitability_score = _normalize_category(metrics)

    # Growth: preserve revenue and earnings growth for every sector.
    metrics = []
    for value, name in ((revenue_growth, "Revenue"), (earnings_growth, "Earnings")):
        if value is None:
            continue
        points = (
            10 if value >= 20 else 8 if value >= 10 else 6 if value >= 5 else 4 if value >= 0 else 0
        )
        reasons.append(f"{name} growth is {value:.2f}%.")
        metrics.append((points, 10))
    growth_score = _normalize_category(metrics)

    # Banks: debt/equity, current ratio, cash/debt and cash-flow measures
    # are not scored because they are not comparable to non-financial firms.
    if is_bank:
        health_score = None
        cash_flow_score = None
        reasons.append(
            "Bank detected: debt/liquidity and operating/free-cash-flow metrics excluded from scoring."
        )
    else:
        metrics = []
        debt_to_equity = _debt_equity_ratio(data.get("debt_to_equity"))
        current_ratio = to_float(data.get("current_ratio"))
        if current_ratio is not None and current_ratio <= 0:
            current_ratio = None
        total_debt, total_cash = to_float(data.get("total_debt")), to_float(data.get("total_cash"))
        if total_debt is not None and total_debt < 0:
            total_debt = None
        if total_cash is not None and total_cash < 0:
            total_cash = None
        if debt_to_equity is not None:
            points = (
                8
                if debt_to_equity <= 0.30
                else (
                    7
                    if debt_to_equity <= 0.75
                    else 5 if debt_to_equity <= 1.5 else 3 if debt_to_equity <= 2 else 0
                )
            )
            reasons.append(f"Debt-to-equity of {debt_to_equity:.2f}x.")
            metrics.append((points, 8))
        if current_ratio is not None:
            points = (
                7
                if 1.5 <= current_ratio <= 3
                else 5 if current_ratio >= 1 else 2 if current_ratio >= 0.75 else 0
            )
            reasons.append(f"Current ratio of {current_ratio:.2f}x.")
            metrics.append((points, 7))
        if total_cash is not None and total_debt is not None:
            ratio = float("inf") if total_debt <= 0 else total_cash / total_debt
            points = 5 if ratio >= 1 else 4 if ratio >= 0.5 else 2 if ratio >= 0.25 else 0
            reasons.append("Cash coverage of reported debt assessed.")
            metrics.append((points, 5))
        health_score = _normalize_category(metrics)

        metrics = []
        for value, name in (
            (to_float(data.get("operating_cash_flow")), "Operating cash flow"),
            (to_float(data.get("free_cash_flow")), "Free cash flow"),
        ):
            if value is None:
                continue
            points = 10 if value > 0 else 3 if value == 0 else 0
            reasons.append(
                f"{name} is {'positive' if value > 0 else 'approximately neutral' if value == 0 else 'negative'}."
            )
            metrics.append((points, 10))
        cash_flow_score = _normalize_category(metrics)

    available_scores = [
        score
        for score in (
            valuation_score,
            profitability_score,
            growth_score,
            health_score,
            cash_flow_score,
        )
        if score is not None
    ]
    if not available_scores:
        return None, ["Insufficient fundamental data to calculate a score."]
    final_score = round(max(0, min((sum(available_scores) / len(available_scores)) * 5, 100)))
    return final_score, reasons
