import yfinance as yf

from services.sotp_financial_asset_policy_service import (
    evaluate_financial_asset_policy,
)


def _to_crore(value):
    try:
        if value is None:
            return None

        value = float(value)

        if value != value:
            return None

        return value / 1e7

    except (TypeError, ValueError):
        return None


def analyze_financial_asset_evidence(symbol: str) -> dict:
    """
    Build historical evidence supporting economic classification
    of the non-current financial asset pool.

    IMPORTANT:
    Interest income is used only as supporting evidence that
    non-operating financial activity exists. It is NOT assumed
    to have been generated exclusively by Investment in
    Financial Assets.
    """

    policy = evaluate_financial_asset_policy(symbol)

    if not isinstance(policy, dict) or policy.get("status") != "OK":
        return {
            "status": "UNAVAILABLE",
            "symbol": symbol,
            "message": "Financial asset policy is unavailable.",
        }

    ticker_symbol = symbol if str(symbol).upper().endswith(".NS") else f"{str(symbol).upper()}.NS"

    try:
        ticker = yf.Ticker(ticker_symbol)

        balance_sheet = ticker.balance_sheet
        income_statement = ticker.income_stmt

    except Exception as exc:
        return {
            "status": "UNAVAILABLE",
            "symbol": symbol,
            "message": f"Unable to retrieve financial statements: {exc}",
        }

    if balance_sheet is None or balance_sheet.empty:
        return {
            "status": "UNAVAILABLE",
            "symbol": symbol,
            "message": "Balance sheet is unavailable.",
        }

    if income_statement is None or income_statement.empty:
        return {
            "status": "UNAVAILABLE",
            "symbol": symbol,
            "message": "Income statement is unavailable.",
        }

    financial_asset_row = "Investmentin Financial Assets"
    interest_income_row = "Interest Income Non Operating"

    history = []

    common_periods = [
        period for period in balance_sheet.columns if period in income_statement.columns
    ]

    for period in common_periods[:4]:

        financial_assets = None
        interest_income = None

        if financial_asset_row in balance_sheet.index:
            financial_assets = _to_crore(
                balance_sheet.loc[
                    financial_asset_row,
                    period,
                ]
            )

        if interest_income_row in income_statement.index:
            interest_income = _to_crore(
                income_statement.loc[
                    interest_income_row,
                    period,
                ]
            )

        diagnostic_yield = None

        if (
            isinstance(financial_assets, (int, float))
            and financial_assets > 0
            and isinstance(interest_income, (int, float))
        ):
            diagnostic_yield = interest_income / financial_assets

        history.append(
            {
                "period": str(period),
                "financial_assets": financial_assets,
                "non_operating_interest_income": interest_income,
                "diagnostic_yield": diagnostic_yield,
                "diagnostic_yield_percent": (
                    round(diagnostic_yield * 100, 2)
                    if isinstance(diagnostic_yield, (int, float))
                    else None
                ),
            }
        )

    valid_asset_periods = [
        row
        for row in history
        if isinstance(
            row.get("financial_assets"),
            (int, float),
        )
        and row["financial_assets"] > 0
    ]

    valid_income_periods = [
        row
        for row in history
        if isinstance(
            row.get("non_operating_interest_income"),
            (int, float),
        )
        and row["non_operating_interest_income"] > 0
    ]

    valid_yields = [
        row["diagnostic_yield"]
        for row in history
        if isinstance(
            row.get("diagnostic_yield"),
            (int, float),
        )
        and row["diagnostic_yield"] > 0
    ]

    persistent_financial_assets = len(valid_asset_periods) >= 3

    persistent_non_operating_income = len(valid_income_periods) >= 3

    yield_stability = None

    if len(valid_yields) >= 3:
        mean_yield = sum(valid_yields) / len(valid_yields)

        spread = max(valid_yields) - min(valid_yields)

        yield_stability = {
            "mean_yield": round(mean_yield, 4),
            "mean_yield_percent": round(
                mean_yield * 100,
                2,
            ),
            "min_yield_percent": round(
                min(valid_yields) * 100,
                2,
            ),
            "max_yield_percent": round(
                max(valid_yields) * 100,
                2,
            ),
            "spread_percent_points": round(
                spread * 100,
                2,
            ),
            "stable": spread <= 0.03,
        }

    evidence_score = 0

    if persistent_financial_assets:
        evidence_score += 35

    if persistent_non_operating_income:
        evidence_score += 35

    if isinstance(yield_stability, dict) and yield_stability.get("stable"):
        evidence_score += 15

    reconciliation = policy.get(
        "financial_asset_reconciliation",
        {},
    )

    if reconciliation.get("reconciles"):
        evidence_score += 15

    evidence_score = min(evidence_score, 100)

    if evidence_score >= 80:
        evidence_view = "STRONG"
    elif evidence_score >= 60:
        evidence_view = "MODERATE"
    else:
        evidence_view = "WEAK"

    return {
        "status": "OK",
        "symbol": policy.get("symbol", symbol),
        "ticker": ticker_symbol,
        "currency": policy.get("currency", "INR"),
        "unit": policy.get("unit", "crore"),
        "history": history,
        "persistence": {
            "financial_asset_periods": len(valid_asset_periods),
            "non_operating_income_periods": len(valid_income_periods),
            "persistent_financial_assets": (persistent_financial_assets),
            "persistent_non_operating_income": (persistent_non_operating_income),
        },
        "yield_diagnostic": yield_stability,
        "evidence_score": evidence_score,
        "evidence_view": evidence_view,
        "supports_non_operating_classification": (evidence_score >= 80),
        "supports_carrying_value_addition": False,
        "interpretation": (
            "The historical statements show a persistent "
            "non-current financial asset balance together with "
            "persistent non-operating interest income. This "
            "supports the hypothesis that material financial "
            "assets exist outside the segment EBITDA-based "
            "operating valuation. However, the analysis does "
            "not establish that the interest income was "
            "generated exclusively by the reported financial "
            "asset balance."
        ),
        "warnings": [
            (
                "Diagnostic yield is not a portfolio yield and "
                "must not be used to value the financial assets."
            ),
            (
                "Non-operating classification evidence does not "
                "establish that carrying value equals fair value."
            ),
            (
                "Asset-level composition and operating overlap "
                "remain necessary before the balance enters the "
                "SOTP equity bridge."
            ),
        ],
    }
