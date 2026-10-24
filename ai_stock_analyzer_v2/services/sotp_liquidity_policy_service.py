from services.sotp_balance_sheet_detail_service import (
    get_sotp_balance_sheet_details,
)


def evaluate_short_term_investment_policy(symbol: str) -> dict:
    """
    Evaluate whether short-term investments should be included
    as an incremental asset in the SOTP equity bridge.

    This version deliberately uses a conservative policy:
    short-term investments are recognized as a financial asset,
    but are not added to SOTP equity value until the portion
    representing excess liquidity can be established reliably.
    """

    details = get_sotp_balance_sheet_details(symbol)

    if not isinstance(details, dict) or details.get("status") != "OK":
        return {
            "status": "UNAVAILABLE",
            "symbol": symbol,
            "message": "Balance-sheet details are unavailable.",
        }

    cash_data = details.get("cash", {})

    cash = cash_data.get("cash_and_equivalents")
    short_term_investments = cash_data.get("short_term_investments")
    cash_and_sti = cash_data.get("cash_and_short_term_investments")

    # ------------------------------------------------------
    # Validate inputs
    # ------------------------------------------------------

    if not isinstance(short_term_investments, (int, float)):
        return {
            "status": "UNAVAILABLE",
            "symbol": symbol,
            "message": "Short-term investment balance is unavailable.",
        }

    # ------------------------------------------------------
    # Current V5 policy
    # ------------------------------------------------------

    classification = "TREASURY_LIQUIDITY_ASSET"

    inclusion_status = "PENDING_EXCESS_LIQUIDITY_TEST"

    included_value = 0.0

    excluded_pending_value = float(short_term_investments)

    # ------------------------------------------------------
    # Reconciliation
    # ------------------------------------------------------

    reconciles = False
    reconciliation_gap = None

    if all(
        isinstance(value, (int, float)) for value in [cash, short_term_investments, cash_and_sti]
    ):
        reconciliation_gap = float(cash) + float(short_term_investments) - float(cash_and_sti)

        reconciles = abs(reconciliation_gap) < 1.0

    return {
        "status": "OK",
        "symbol": symbol,
        "currency": details.get("currency", "INR"),
        "unit": details.get("unit", "crore"),
        "period": details.get("period"),
        "classification": classification,
        "reported_short_term_investments": short_term_investments,
        "cash_and_equivalents": cash,
        "cash_and_short_term_investments": cash_and_sti,
        "reconciliation": {
            "cash_plus_short_term_reconciles": reconciles,
            "reconciliation_gap": reconciliation_gap,
        },
        "sotp_policy": {
            "status": inclusion_status,
            "included_value": included_value,
            "pending_value": excluded_pending_value,
            "treatment": "DO_NOT_ADD_YET",
        },
        "interpretation": (
            "Short-term investments are a recurring treasury liquidity "
            "asset distinct from cash and equivalents. However, the "
            "available balance-sheet evidence does not establish what "
            "portion represents excess liquidity beyond operating and "
            "financing requirements. The balance is therefore excluded "
            "from the current SOTP equity bridge pending a defensible "
            "excess-liquidity methodology."
        ),
        "warnings": [
            (
                "The reported short-term investment balance must not be "
                "automatically treated as excess cash."
            ),
            (
                "The balance is economically distinct from cash and "
                "equivalents but appears to form part of the company's "
                "recurring liquidity and treasury structure."
            ),
            (
                "A future SOTP version may include a portion of this "
                "balance after establishing a defensible minimum "
                "liquidity requirement."
            ),
        ],
    }
