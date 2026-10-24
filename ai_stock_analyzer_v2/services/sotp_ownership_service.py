from services.sotp_balance_sheet_detail_service import (
    get_sotp_balance_sheet_details,
)

# ==========================================================
# HELPERS
# ==========================================================


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


# ==========================================================
# OWNERSHIP / NCI ADJUSTMENT ENGINE
# ==========================================================


def generate_sotp_ownership_adjustment(symbol):
    """
    Determine the ownership adjustment required when
    converting consolidated SOTP enterprise value into
    equity value attributable to parent shareholders.

    V5 currently uses reported balance-sheet minority
    interest as the conservative NCI adjustment.

    This treatment assumes operating segment financials
    are consolidated on a 100% basis.

    A later version may replace book-value NCI with
    segment-specific market-value ownership adjustments.
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

    ownership = details.get(
        "ownership",
        {},
    )

    if not isinstance(ownership, dict):
        ownership = {}

    minority_interest = _safe_float(ownership.get("minority_interest"))

    # ======================================================
    # NCI TREATMENT
    # ======================================================

    if minority_interest is None:

        return {
            "status": "PARTIAL",
            "symbol": symbol,
            "period": details.get("period"),
            "currency": "INR",
            "unit": "crore",
            "minority_interest": None,
            "ownership_adjustment": None,
            "treatment": "UNAVAILABLE",
            "message": ("Minority interest is unavailable."),
        }

    #
    # Current V5 policy:
    #
    # Segment EBITDA is valued on a consolidated basis.
    # Reported minority interest is therefore deducted
    # from consolidated enterprise value when deriving
    # parent equity value.
    #
    # The adjustment is negative because it reduces
    # value attributable to parent shareholders.
    #

    ownership_adjustment = -minority_interest

    return {
        "status": "OK",
        "symbol": symbol,
        "period": details.get("period"),
        "currency": "INR",
        "unit": "crore",
        "minority_interest": round(
            minority_interest,
            2,
        ),
        "ownership_adjustment": round(
            ownership_adjustment,
            2,
        ),
        "treatment": ("DEDUCT_REPORTED_MINORITY_INTEREST"),
        "basis": ("Consolidated operating segment valuation"),
        "reliability": 0.70,
        "interpretation": (
            "Reported minority interest is deducted "
            "from consolidated SOTP enterprise value "
            "to estimate equity value attributable to "
            "parent shareholders."
        ),
        "limitations": [
            (
                "Reported minority interest is an "
                "accounting carrying value rather than "
                "a direct market valuation of NCI."
            ),
            (
                "The adjustment assumes the operating "
                "segment EBITDA values used in SOTP are "
                "reported on a consolidated 100% basis."
            ),
            (
                "Future versions should use explicit "
                "ownership percentages and segment-level "
                "market values where reliable data is "
                "available."
            ),
        ],
    }
