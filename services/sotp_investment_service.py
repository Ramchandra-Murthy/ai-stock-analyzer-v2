from services.sotp_balance_sheet_detail_service import (
    get_sotp_balance_sheet_details,
)

# ==========================================================
# HELPERS
# ==========================================================


def _safe_float(value):
    """Convert value to finite float or return None."""

    try:
        if value is None:
            return None

        value = float(value)

        if value != value:
            return None

        return value

    except (TypeError, ValueError):
        return None


def _round_value(value):
    if value is None:
        return None

    return round(value, 2)


# ==========================================================
# SOTP INVESTMENT CLASSIFICATION
# ==========================================================


def generate_sotp_investment_adjustment(symbol):
    """
    Classify investment assets for SOTP V5.

    IMPORTANT:

    This service does NOT automatically add every reported
    investment balance to equity value.

    It separates:

    1. short-term investments
    2. financial investment balance
    3. long-term equity investments
    4. JV investments
    5. associate investments

    and checks for obvious accounting overlap.

    Monetary values are INR crore.
    """

    details = get_sotp_balance_sheet_details(symbol)

    if not isinstance(details, dict):
        return {
            "status": "UNAVAILABLE",
            "symbol": symbol,
            "message": "Invalid balance-sheet detail result.",
        }

    if details.get("status") != "OK":
        return {
            "status": "UNAVAILABLE",
            "symbol": symbol,
            "message": details.get(
                "message",
                "Balance-sheet details unavailable.",
            ),
        }

    cash = details.get("cash", {})
    investments = details.get("investments", {})

    if not isinstance(cash, dict):
        cash = {}

    if not isinstance(investments, dict):
        investments = {}

    short_term_investments = _safe_float(cash.get("short_term_investments"))

    financial_investments = _safe_float(investments.get("financial_investments"))

    long_term_equity = _safe_float(investments.get("long_term_equity_investment"))

    joint_ventures = _safe_float(investments.get("joint_venture_investments"))

    associates = _safe_float(investments.get("associate_investments"))

    # ======================================================
    # LONG-TERM EQUITY RECONCILIATION
    # ======================================================

    jv_associate_sum = None
    long_term_equity_gap = None
    long_term_components_reconcile = False

    if joint_ventures is not None and associates is not None:
        jv_associate_sum = joint_ventures + associates

    if long_term_equity is not None and jv_associate_sum is not None:
        long_term_equity_gap = long_term_equity - jv_associate_sum

        long_term_components_reconcile = abs(long_term_equity_gap) <= 1.0

    # ======================================================
    # SHORT-TERM / FINANCIAL INVESTMENT COMPARISON
    # ======================================================

    short_financial_difference = None
    short_financial_ratio = None
    possible_overlap = False

    if short_term_investments is not None and financial_investments is not None:
        short_financial_difference = short_term_investments - financial_investments

        if short_term_investments != 0:
            short_financial_ratio = financial_investments / short_term_investments

            possible_overlap = 0.90 <= short_financial_ratio <= 1.10

    # ======================================================
    # CURRENT V5 TREATMENT
    # ======================================================

    #
    # We have strong evidence that JV + associate balances
    # reconcile to the long-term equity investment balance.
    #
    # Therefore only the parent long-term equity balance
    # should be considered, not all three separately.
    #
    # We do NOT yet have sufficient evidence that the
    # financial investment balance is independent of the
    # short-term investment balance.
    #
    # Consequently:
    #
    # - ST investments remain REVIEW.
    # - Financial investments remain REVIEW.
    # - Long-term equity investment remains REVIEW.
    # - JV/associate values are SUBCOMPONENTS.
    #

    investment_adjustment = None

    return {
        "status": "OK",
        "symbol": symbol,
        "period": details.get("period"),
        "currency": "INR",
        "unit": "crore",
        "reported_balances": {
            "short_term_investments": _round_value(short_term_investments),
            "financial_investments": _round_value(financial_investments),
            "long_term_equity_investment": _round_value(long_term_equity),
            "joint_venture_investments": _round_value(joint_ventures),
            "associate_investments": _round_value(associates),
        },
        "reconciliation": {
            "jv_plus_associates": _round_value(jv_associate_sum),
            "long_term_equity_gap": _round_value(long_term_equity_gap),
            "long_term_components_reconcile": (long_term_components_reconcile),
            "short_term_minus_financial": _round_value(short_financial_difference),
            "financial_to_short_term_ratio": (
                round(
                    short_financial_ratio,
                    4,
                )
                if short_financial_ratio is not None
                else None
            ),
            "possible_short_financial_overlap": (possible_overlap),
        },
        "classification": {
            "short_term_investments": "REVIEW",
            "financial_investments": "REVIEW",
            "long_term_equity_investment": "REVIEW",
            "joint_venture_investments": ("SUBCOMPONENT_OF_LONG_TERM_EQUITY"),
            "associate_investments": ("SUBCOMPONENT_OF_LONG_TERM_EQUITY"),
        },
        "investment_adjustment": (investment_adjustment),
        "adjustment_status": "PENDING",
        "warnings": [
            (
                "JV and associate investment balances "
                "must not be added separately when they "
                "are already included in long-term equity "
                "investment."
            ),
            (
                "Short-term investments and financial "
                "investments are similar in magnitude and "
                "may overlap. They must not both be added "
                "to SOTP equity value without confirming "
                "their accounting composition."
            ),
            (
                "Investment carrying values may differ "
                "materially from market or realizable value."
            ),
        ],
    }


# ==========================================================
# INVESTMENT HIERARCHY ANALYSIS
# ==========================================================


def analyze_sotp_investment_hierarchy(symbol):
    """
    Analyze reported cash and investment balances for
    accounting overlap before they enter the SOTP bridge.

    This function establishes only relationships that can
    be reconciled from the reported balance-sheet rows.

    It deliberately avoids assuming that similarly sized
    balances represent the same accounting assets.
    """

    details = get_sotp_balance_sheet_details(symbol)

    if not isinstance(details, dict):
        return {
            "status": "UNAVAILABLE",
            "symbol": symbol,
            "message": "Invalid balance-sheet detail result.",
        }

    if details.get("status") != "OK":
        return {
            "status": "UNAVAILABLE",
            "symbol": symbol,
            "message": details.get(
                "message",
                "Balance-sheet details unavailable.",
            ),
        }

    cash = details.get("cash", {})
    investments = details.get("investments", {})

    if not isinstance(cash, dict):
        cash = {}

    if not isinstance(investments, dict):
        investments = {}

    cash_equivalents = _safe_float(cash.get("cash_and_equivalents"))

    short_term_investments = _safe_float(cash.get("short_term_investments"))

    cash_and_short_term = _safe_float(cash.get("cash_and_short_term_investments"))

    financial_investments = _safe_float(investments.get("financial_investments"))

    long_term_equity = _safe_float(investments.get("long_term_equity_investment"))

    joint_ventures = _safe_float(investments.get("joint_venture_investments"))

    associates = _safe_float(investments.get("associate_investments"))

    # ======================================================
    # CASH + SHORT-TERM INVESTMENT RECONCILIATION
    # ======================================================

    calculated_cash_short_term = None
    cash_short_term_gap = None
    cash_short_term_reconciles = False

    if cash_equivalents is not None and short_term_investments is not None:
        calculated_cash_short_term = cash_equivalents + short_term_investments

    if calculated_cash_short_term is not None and cash_and_short_term is not None:
        cash_short_term_gap = cash_and_short_term - calculated_cash_short_term

        cash_short_term_reconciles = abs(cash_short_term_gap) <= 1.0

    # ======================================================
    # LONG-TERM EQUITY RECONCILIATION
    # ======================================================

    calculated_long_term_equity = None
    long_term_gap = None
    long_term_reconciles = False

    if joint_ventures is not None and associates is not None:
        calculated_long_term_equity = joint_ventures + associates

    if calculated_long_term_equity is not None and long_term_equity is not None:
        long_term_gap = long_term_equity - calculated_long_term_equity

        long_term_reconciles = abs(long_term_gap) <= 1.0

    # ======================================================
    # FINANCIAL / SHORT-TERM COMPARISON
    # ======================================================

    financial_short_term_gap = None
    financial_short_term_ratio = None

    if financial_investments is not None and short_term_investments is not None:
        financial_short_term_gap = short_term_investments - financial_investments

        if short_term_investments != 0:
            financial_short_term_ratio = financial_investments / short_term_investments

    possible_overlap = False

    if financial_short_term_ratio is not None:
        possible_overlap = 0.90 <= financial_short_term_ratio <= 1.10

    # ======================================================
    # CLASSIFICATION
    # ======================================================

    hierarchy = {
        "cash_and_short_term_investments": {
            "value": _round_value(cash_and_short_term),
            "classification": "AGGREGATE",
            "components": [
                "cash_and_equivalents",
                "short_term_investments",
            ],
            "reconciles": cash_short_term_reconciles,
        },
        "cash_and_equivalents": {
            "value": _round_value(cash_equivalents),
            "classification": ("COMPONENT_OF_CASH_AND_SHORT_TERM"),
        },
        "short_term_investments": {
            "value": _round_value(short_term_investments),
            "classification": ("COMPONENT_OF_CASH_AND_SHORT_TERM"),
        },
        "financial_investments": {
            "value": _round_value(financial_investments),
            "classification": "REVIEW",
            "possible_overlap_with": ("short_term_investments" if possible_overlap else None),
        },
        "long_term_equity_investment": {
            "value": _round_value(long_term_equity),
            "classification": "AGGREGATE",
            "components": [
                "joint_venture_investments",
                "associate_investments",
            ],
            "reconciles": long_term_reconciles,
        },
        "joint_venture_investments": {
            "value": _round_value(joint_ventures),
            "classification": ("COMPONENT_OF_LONG_TERM_EQUITY"),
        },
        "associate_investments": {
            "value": _round_value(associates),
            "classification": ("COMPONENT_OF_LONG_TERM_EQUITY"),
        },
    }

    return {
        "status": "OK",
        "symbol": symbol,
        "period": details.get("period"),
        "currency": "INR",
        "unit": "crore",
        "hierarchy": hierarchy,
        "reconciliation": {
            "cash_plus_short_term": _round_value(calculated_cash_short_term),
            "reported_cash_and_short_term": _round_value(cash_and_short_term),
            "cash_short_term_gap": _round_value(cash_short_term_gap),
            "cash_short_term_reconciles": (cash_short_term_reconciles),
            "jv_plus_associates": _round_value(calculated_long_term_equity),
            "reported_long_term_equity": _round_value(long_term_equity),
            "long_term_gap": _round_value(long_term_gap),
            "long_term_reconciles": (long_term_reconciles),
            "short_term_minus_financial": _round_value(financial_short_term_gap),
            "financial_to_short_term_ratio": (
                round(
                    financial_short_term_ratio,
                    4,
                )
                if financial_short_term_ratio is not None
                else None
            ),
            "possible_financial_short_term_overlap": (possible_overlap),
        },
        "valuation_treatment": {
            "cash_and_equivalents": "ALREADY_IN_NET_DEBT",
            "short_term_investments": "REVIEW",
            "financial_investments": "REVIEW",
            "long_term_equity_investment": "REVIEW",
            "joint_venture_investments": "DO_NOT_ADD_SEPARATELY",
            "associate_investments": "DO_NOT_ADD_SEPARATELY",
        },
        "warnings": [
            (
                "Cash and short-term investments reconcile "
                "exactly to the reported aggregate and must "
                "not be added independently without regard "
                "to the net-debt definition."
            ),
            (
                "Financial investments and short-term "
                "investments are similar in magnitude, but "
                "their accounting relationship has not yet "
                "been established."
            ),
            (
                "JV and associate balances reconcile to "
                "long-term equity investment and therefore "
                "must not be added separately."
            ),
        ],
    }


# ==========================================================
# FINANCIAL ASSET COMPOSITION
# ==========================================================


def analyze_financial_asset_composition(symbol):
    """
    Analyze the composition of reported financial investment
    assets for SOTP V5.

    The upstream balance sheet reports:

    Investment in Financial Assets
        = Available For Sale Securities
        + Financial Assets Designated at FVTPL

    when the reported rows reconcile.

    This function establishes that hierarchy while avoiding
    any assumption that the financial-asset aggregate is the
    same accounting pool as Other Short Term Investments.
    """

    import yfinance as yf

    normalized_symbol = str(symbol).upper().strip()

    if not normalized_symbol.endswith(".NS"):
        ticker_symbol = f"{normalized_symbol}.NS"
    else:
        ticker_symbol = normalized_symbol

    try:
        ticker = yf.Ticker(ticker_symbol)
        balance_sheet = ticker.balance_sheet

    except Exception as error:
        return {
            "status": "UNAVAILABLE",
            "symbol": symbol,
            "message": str(error),
        }

    if balance_sheet is None or balance_sheet.empty:
        return {
            "status": "UNAVAILABLE",
            "symbol": symbol,
            "message": "Balance sheet unavailable.",
        }

    period = balance_sheet.columns[0]

    # ======================================================
    # ROW READER
    # ======================================================

    def get_row_crore(row_name):

        if row_name not in balance_sheet.index:
            return None

        value = _safe_float(
            balance_sheet.loc[
                row_name,
                period,
            ]
        )

        if value is None:
            return None

        # Yahoo values are INR absolute.
        # Convert to INR crore.
        return value / 1e7

    # ======================================================
    # FINANCIAL ASSET BALANCES
    # ======================================================

    financial_assets = get_row_crore("Investmentin Financial Assets")

    available_for_sale = get_row_crore("Available For Sale Securities")

    fvtpl_assets = get_row_crore(
        "Financial Assets Designatedas Fair Value Through Profitor Loss Total"
    )

    short_term_investments = get_row_crore("Other Short Term Investments")

    # ======================================================
    # FINANCIAL-ASSET RECONCILIATION
    # ======================================================

    calculated_financial_assets = None
    financial_asset_gap = None
    financial_assets_reconcile = False

    if available_for_sale is not None and fvtpl_assets is not None:
        calculated_financial_assets = available_for_sale + fvtpl_assets

    if calculated_financial_assets is not None and financial_assets is not None:
        financial_asset_gap = financial_assets - calculated_financial_assets

        financial_assets_reconcile = abs(financial_asset_gap) <= 1.0

    # ======================================================
    # SHORT-TERM COMPARISON
    # ======================================================

    short_term_gap = None
    financial_to_short_term_ratio = None
    possible_overlap = False

    if financial_assets is not None and short_term_investments is not None:
        short_term_gap = short_term_investments - financial_assets

        if short_term_investments != 0:
            financial_to_short_term_ratio = financial_assets / short_term_investments

            possible_overlap = 0.90 <= financial_to_short_term_ratio <= 1.10

    # ======================================================
    # CLASSIFICATION
    # ======================================================

    return {
        "status": "OK",
        "symbol": normalized_symbol.replace(
            ".NS",
            "",
        ),
        "ticker": ticker_symbol,
        "period": str(period),
        "currency": "INR",
        "unit": "crore",
        "financial_assets": {
            "investment_in_financial_assets": _round_value(financial_assets),
            "available_for_sale_securities": _round_value(available_for_sale),
            "fvtpl_financial_assets": _round_value(fvtpl_assets),
            "other_short_term_investments": _round_value(short_term_investments),
        },
        "reconciliation": {
            "afs_plus_fvtpl": _round_value(calculated_financial_assets),
            "reported_financial_assets": _round_value(financial_assets),
            "financial_asset_gap": _round_value(financial_asset_gap),
            "financial_assets_reconcile": (financial_assets_reconcile),
            "short_term_minus_financial_assets": _round_value(short_term_gap),
            "financial_to_short_term_ratio": (
                round(
                    financial_to_short_term_ratio,
                    4,
                )
                if financial_to_short_term_ratio is not None
                else None
            ),
            "possible_short_term_overlap": (possible_overlap),
        },
        "hierarchy": {
            "investment_in_financial_assets": {
                "classification": "AGGREGATE",
                "components": [
                    "available_for_sale_securities",
                    "fvtpl_financial_assets",
                ],
                "reconciles": (financial_assets_reconcile),
            },
            "available_for_sale_securities": {
                "classification": ("COMPONENT_OF_FINANCIAL_ASSETS"),
            },
            "fvtpl_financial_assets": {
                "classification": ("COMPONENT_OF_FINANCIAL_ASSETS"),
            },
            "other_short_term_investments": {
                "classification": "REVIEW",
                "possible_overlap_with": (
                    "investment_in_financial_assets" if possible_overlap else None
                ),
            },
        },
        "valuation_treatment": {
            "investment_in_financial_assets": "REVIEW",
            "available_for_sale_securities": ("DO_NOT_ADD_SEPARATELY"),
            "fvtpl_financial_assets": ("DO_NOT_ADD_SEPARATELY"),
            "other_short_term_investments": "REVIEW",
        },
        "warnings": [
            (
                "Available-for-sale securities and FVTPL "
                "financial assets reconcile to the reported "
                "Investment in Financial Assets aggregate "
                "and must not be added separately."
            ),
            (
                "The financial-assets aggregate is close "
                "to Other Short Term Investments, but the "
                "reported balance-sheet hierarchy does not "
                "establish that the two balances represent "
                "the same accounting pool."
            ),
            (
                "No financial-investment balance should "
                "enter the SOTP equity bridge until its "
                "relationship with operating assets and "
                "the net-debt definition is resolved."
            ),
        ],
    }
