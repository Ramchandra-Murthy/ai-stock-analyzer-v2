# ==========================================================
# SOTP V5 - EQUITY BRIDGE ADJUSTMENT DATA
# ==========================================================


SOTP_ADJUSTMENT_DATA = {
    "RELIANCE": {
        "period": "FY2025-26",
        "currency": "INR",
        "unit": "crore",
        "new_energy": {
            "value": None,
            "source": None,
            "reliability": None,
            "available": False,
            "method": "STRATEGIC_VALUE",
        },
        "other_investments": {
            "value": None,
            "source": None,
            "reliability": None,
            "available": False,
            "method": "ASSET_VALUE",
        },
        "gross_debt": {
            "value": None,
            "source": None,
            "reliability": None,
            "available": False,
        },
        "cash_and_equivalents": {
            "value": None,
            "source": None,
            "reliability": None,
            "available": False,
        },
        "other_debt_adjustments": {
            "value": None,
            "source": None,
            "reliability": None,
            "available": False,
        },
        "minority_interest": {
            "value": None,
            "source": None,
            "reliability": None,
            "available": False,
        },
    },
}


# ==========================================================
# HELPERS
# ==========================================================


def _clean_symbol(symbol):
    """Normalize NSE symbol."""

    if not symbol:
        return ""

    symbol = str(symbol).strip().upper()

    if symbol.endswith(".NS"):
        symbol = symbol[:-3]

    return symbol


# ==========================================================
# DATA ACCESS
# ==========================================================


def get_sotp_adjustment_data(symbol):
    """
    Return SOTP V5 equity-bridge adjustment data.

    Missing values remain explicitly unavailable rather
    than being silently assumed to be zero.
    """

    base_symbol = _clean_symbol(symbol)

    company_data = SOTP_ADJUSTMENT_DATA.get(base_symbol)

    if not isinstance(company_data, dict):
        return {
            "status": "UNAVAILABLE",
            "symbol": base_symbol,
            "message": ("SOTP adjustment data is not configured " "for this company."),
        }

    adjustment_keys = [
        "new_energy",
        "other_investments",
        "gross_debt",
        "cash_and_equivalents",
        "other_debt_adjustments",
        "minority_interest",
    ]

    adjustments = {}

    available_count = 0

    for key in adjustment_keys:

        block = company_data.get(key, {})

        if not isinstance(block, dict):
            block = {}

        result = dict(block)

        if result.get("available") is True:
            available_count += 1

        adjustments[key] = result

    total_count = len(adjustment_keys)

    coverage = available_count / total_count if total_count > 0 else 0.0

    return {
        "status": "OK",
        "symbol": base_symbol,
        "period": company_data.get("period"),
        "currency": company_data.get(
            "currency",
            "INR",
        ),
        "unit": company_data.get(
            "unit",
            "crore",
        ),
        "adjustment_count": total_count,
        "available_adjustment_count": available_count,
        "coverage": round(
            coverage,
            4,
        ),
        "coverage_percent": round(
            coverage * 100.0,
            1,
        ),
        "adjustments": adjustments,
    }
