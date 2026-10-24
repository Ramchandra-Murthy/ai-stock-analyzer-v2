from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def round_currency(amount: float | Decimal, places: int = 2) -> Decimal:
    """Round a monetary amount using standard financial half-up rounding."""
    d_amount = Decimal(str(amount))
    quantizer = Decimal("1.0" if places == 0 else "0." + "0" * places)
    return d_amount.quantize(quantizer, rounding=ROUND_HALF_UP)
