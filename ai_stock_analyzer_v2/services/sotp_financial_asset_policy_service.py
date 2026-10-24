import yfinance as yf

CRORE = 1e7


def _value_in_crore(balance_sheet, row, column):
    """
    Safely extract a balance-sheet value and convert INR to crore.
    """

    if row not in balance_sheet.index:
        return None

    value = balance_sheet.loc[row, column]

    try:
        if value != value:
            return None

        return round(float(value) / CRORE, 2)

    except (TypeError, ValueError):
        return None


def evaluate_financial_asset_policy(symbol: str) -> dict:
    """
    Analyze Reliance's non-current financial investment assets for
    possible inclusion in the SOTP equity bridge.

    The aggregate Investment in Financial Assets is treated as the
    controlling balance. AFS and FVTPL balances are components only
    and must never be added separately.
    """

    normalized_symbol = symbol.upper().replace(".NS", "")
    ticker_symbol = f"{normalized_symbol}.NS"

    try:
        ticker = yf.Ticker(ticker_symbol)
        balance_sheet = ticker.balance_sheet

    except Exception as error:
        return {
            "status": "UNAVAILABLE",
            "symbol": normalized_symbol,
            "message": str(error),
        }

    if balance_sheet is None or balance_sheet.empty:
        return {
            "status": "UNAVAILABLE",
            "symbol": normalized_symbol,
            "message": "Balance sheet is unavailable.",
        }

    column = balance_sheet.columns[0]

    financial_assets = _value_in_crore(
        balance_sheet,
        "Investmentin Financial Assets",
        column,
    )

    afs = _value_in_crore(
        balance_sheet,
        "Available For Sale Securities",
        column,
    )

    fvtpl = _value_in_crore(
        balance_sheet,
        "Financial Assets Designatedas Fair Value Through Profitor Loss Total",
        column,
    )

    long_term_equity = _value_in_crore(
        balance_sheet,
        "Long Term Equity Investment",
        column,
    )

    joint_ventures = _value_in_crore(
        balance_sheet,
        "Investmentsin Joint Venturesat Cost",
        column,
    )

    associates = _value_in_crore(
        balance_sheet,
        "Investmentsin Associatesat Cost",
        column,
    )

    # ------------------------------------------------------
    # Financial-asset reconciliation
    # ------------------------------------------------------

    financial_component_total = None
    financial_gap = None
    financial_reconciles = False

    if isinstance(afs, (int, float)) and isinstance(fvtpl, (int, float)):
        financial_component_total = round(afs + fvtpl, 2)

    if isinstance(financial_assets, (int, float)) and isinstance(
        financial_component_total, (int, float)
    ):
        financial_gap = round(
            financial_assets - financial_component_total,
            2,
        )

        financial_reconciles = abs(financial_gap) < 1.0

    # ------------------------------------------------------
    # Long-term-equity reconciliation
    # ------------------------------------------------------

    equity_component_total = None
    equity_gap = None
    equity_reconciles = False

    if isinstance(joint_ventures, (int, float)) and isinstance(associates, (int, float)):
        equity_component_total = round(
            joint_ventures + associates,
            2,
        )

    if isinstance(long_term_equity, (int, float)) and isinstance(
        equity_component_total, (int, float)
    ):
        equity_gap = round(
            long_term_equity - equity_component_total,
            2,
        )

        equity_reconciles = abs(equity_gap) < 1.0

    # ------------------------------------------------------
    # SOTP classification
    # ------------------------------------------------------

    if financial_reconciles:
        classification = "NON_OPERATING_FINANCIAL_ASSET_CANDIDATE"
        policy_status = "PENDING_OPERATING_OVERLAP_REVIEW"
    else:
        classification = "UNRESOLVED_FINANCIAL_ASSET"
        policy_status = "PENDING_RECONCILIATION"

    return {
        "status": "OK",
        "symbol": normalized_symbol,
        "ticker": ticker_symbol,
        "period": str(column),
        "currency": "INR",
        "unit": "crore",
        "financial_assets": {
            "aggregate": financial_assets,
            "available_for_sale_securities": afs,
            "fvtpl_financial_assets": fvtpl,
            "component_total": financial_component_total,
        },
        "financial_asset_reconciliation": {
            "gap": financial_gap,
            "reconciles": financial_reconciles,
        },
        "long_term_equity_investments": {
            "aggregate": long_term_equity,
            "joint_ventures": joint_ventures,
            "associates": associates,
            "component_total": equity_component_total,
        },
        "long_term_equity_reconciliation": {
            "gap": equity_gap,
            "reconciles": equity_reconciles,
        },
        "classification": classification,
        "sotp_policy": {
            "status": policy_status,
            "included_value": 0.0,
            "pending_value": (
                financial_assets if isinstance(financial_assets, (int, float)) else 0.0
            ),
            "treatment": "DO_NOT_ADD_YET",
        },
        "component_treatment": {
            "investment_in_financial_assets": "CONTROLLING_AGGREGATE",
            "available_for_sale_securities": "COMPONENT_ONLY",
            "fvtpl_financial_assets": "COMPONENT_ONLY",
            "long_term_equity_investment": "SEPARATE_ASSET_POOL",
            "joint_ventures": "COMPONENT_ONLY",
            "associates": "COMPONENT_ONLY",
        },
        "interpretation": (
            "Investment in Financial Assets is a separately reported "
            "non-current financial-asset pool whose AFS and FVTPL "
            "components reconcile to the aggregate. It is therefore a "
            "candidate non-operating asset for SOTP purposes. Inclusion "
            "is deferred until operating overlap and valuation basis are "
            "reviewed."
        ),
        "warnings": [
            (
                "AFS and FVTPL balances are components of Investment in "
                "Financial Assets and must not be added separately."
            ),
            (
                "Long-Term Equity Investment is treated as a separate "
                "asset pool and must not be combined with the financial "
                "asset aggregate without evidence."
            ),
            (
                "Accounting classification alone does not establish that "
                "the entire financial-asset balance is incremental to "
                "operating enterprise value."
            ),
        ],
    }
