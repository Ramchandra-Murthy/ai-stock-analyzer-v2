import yfinance as yf

CRORE_DIVISOR = 10_000_000


def _safe_float(value):
    try:
        if value is None:
            return None

        value = float(value)

        if value != value:
            return None

        return value

    except (TypeError, ValueError):
        return None


def _to_crore(value):
    value = _safe_float(value)

    if value is None:
        return None

    return round(value / CRORE_DIVISOR, 2)


def _get_value(balance_sheet, row_name, column):
    """
    Safely retrieve a balance-sheet value.
    """

    if balance_sheet is None:
        return None

    if row_name not in balance_sheet.index:
        return None

    try:
        return _to_crore(balance_sheet.loc[row_name, column])

    except Exception:
        return None


def get_sotp_balance_sheet_details(symbol):
    """
    Extract detailed balance-sheet information required
    for SOTP equity-value reconciliation.

    Monetary values are returned in INR crore.

    This service does NOT decide whether investments,
    restricted cash, minority interest or lease obligations
    should be added/deducted in the final SOTP model.
    It only extracts and classifies the source data.
    """

    clean_symbol = str(symbol).upper().strip()

    ticker_symbol = clean_symbol if clean_symbol.endswith(".NS") else f"{clean_symbol}.NS"

    try:
        ticker = yf.Ticker(ticker_symbol)
        balance_sheet = ticker.balance_sheet

    except Exception as error:
        return {
            "status": "ERROR",
            "symbol": clean_symbol,
            "message": str(error),
        }

    if balance_sheet is None or balance_sheet.empty:
        return {
            "status": "UNAVAILABLE",
            "symbol": clean_symbol,
            "message": "Balance-sheet data is unavailable.",
        }

    latest_period = balance_sheet.columns[0]

    total_debt = _get_value(
        balance_sheet,
        "Total Debt",
        latest_period,
    )

    provider_net_debt = _get_value(
        balance_sheet,
        "Net Debt",
        latest_period,
    )

    capital_lease_obligations = _get_value(
        balance_sheet,
        "Capital Lease Obligations",
        latest_period,
    )

    minority_interest = _get_value(
        balance_sheet,
        "Minority Interest",
        latest_period,
    )

    financial_investments = _get_value(
        balance_sheet,
        "Investmentin Financial Assets",
        latest_period,
    )

    long_term_equity_investment = _get_value(
        balance_sheet,
        "Long Term Equity Investment",
        latest_period,
    )

    joint_venture_investments = _get_value(
        balance_sheet,
        "Investmentsin Joint Venturesat Cost",
        latest_period,
    )

    associate_investments = _get_value(
        balance_sheet,
        "Investmentsin Associatesat Cost",
        latest_period,
    )

    restricted_cash = _get_value(
        balance_sheet,
        "Restricted Cash",
        latest_period,
    )

    cash_and_short_term_investments = _get_value(
        balance_sheet,
        "Cash Cash Equivalents And Short Term Investments",
        latest_period,
    )

    short_term_investments = _get_value(
        balance_sheet,
        "Other Short Term Investments",
        latest_period,
    )

    cash_and_equivalents = _get_value(
        balance_sheet,
        "Cash And Cash Equivalents",
        latest_period,
    )

    # ======================================================
    # DIAGNOSTIC RECONCILIATIONS
    # ======================================================

    calculated_cash_plus_investments = None

    if cash_and_equivalents is not None and short_term_investments is not None:
        calculated_cash_plus_investments = round(
            cash_and_equivalents + short_term_investments,
            2,
        )

    cash_investment_gap = None

    if cash_and_short_term_investments is not None and calculated_cash_plus_investments is not None:
        cash_investment_gap = round(
            cash_and_short_term_investments - calculated_cash_plus_investments,
            2,
        )

    core_net_debt = None

    if total_debt is not None and cash_and_equivalents is not None:
        core_net_debt = round(
            total_debt - cash_and_equivalents,
            2,
        )

    implied_provider_net_debt = None

    if core_net_debt is not None and capital_lease_obligations is not None:
        implied_provider_net_debt = round(
            core_net_debt - capital_lease_obligations,
            2,
        )

    provider_net_debt_gap = None

    if provider_net_debt is not None and implied_provider_net_debt is not None:
        provider_net_debt_gap = round(
            provider_net_debt - implied_provider_net_debt,
            2,
        )

    return {
        "status": "OK",
        "symbol": clean_symbol,
        "ticker": ticker_symbol,
        "period": str(latest_period),
        "currency": "INR",
        "unit": "crore",
        "debt": {
            "total_debt": total_debt,
            "provider_net_debt": provider_net_debt,
            "capital_lease_obligations": (capital_lease_obligations),
        },
        "cash": {
            "cash_and_equivalents": (cash_and_equivalents),
            "restricted_cash": restricted_cash,
            "cash_and_short_term_investments": (cash_and_short_term_investments),
            "short_term_investments": (short_term_investments),
        },
        "investments": {
            "financial_investments": (financial_investments),
            "long_term_equity_investment": (long_term_equity_investment),
            "joint_venture_investments": (joint_venture_investments),
            "associate_investments": (associate_investments),
        },
        "ownership": {
            "minority_interest": minority_interest,
        },
        "diagnostics": {
            "calculated_cash_plus_investments": (calculated_cash_plus_investments),
            "cash_investment_gap": (cash_investment_gap),
            "core_net_debt": core_net_debt,
            "implied_provider_net_debt": (implied_provider_net_debt),
            "provider_net_debt_gap": (provider_net_debt_gap),
        },
        "warnings": [
            ("Balance-sheet classifications follow the " "upstream data provider taxonomy."),
            (
                "Short-term investments must not automatically "
                "be treated as excess cash in SOTP valuation."
            ),
            (
                "Financial investments may overlap with "
                "subsidiaries, associates, joint ventures or "
                "other separately valued assets."
            ),
            (
                "Capital lease obligations must not be "
                "double-counted if already included in total debt."
            ),
            (
                "Minority interest requires explicit treatment "
                "when converting enterprise value to equity value."
            ),
        ],
    }
