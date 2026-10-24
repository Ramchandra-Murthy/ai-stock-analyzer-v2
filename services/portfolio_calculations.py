"""Portfolio calculations for the personal watchlist.

Only records explicitly marked Bought and containing a positive entry price and
quantity are treated as holdings. Watching records remain visible for alerts,
but are not included in invested value or unrealized P/L.
"""

from __future__ import annotations

from typing import Any


def is_actual_holding(record: dict[str, Any]) -> bool:
    """Return whether a saved record represents a configured, bought position."""
    try:
        entry = float(record.get("entry_price") or 0)
        quantity = float(record.get("quantity") or 0)
    except (TypeError, ValueError):
        return False
    return (
        str(record.get("status") or "Watching").strip().casefold() == "bought"
        and entry > 0
        and quantity > 0
    )


def position_valuation(
    record: dict[str, Any], current_price: float | None
) -> dict[str, float | int | bool | None]:
    """Calculate valuation for a bought position; never value watch-only records."""
    details = record.get("asset_details") or {}
    try:
        quantity = float(record.get("quantity") or 0)
        entry = float(record.get("entry_price") or 0)
        lot_size = (
            int(details.get("lot_size") or 1)
            if details.get("instrument_type") in {"Futures", "Options"}
            else 1
        )
    except (TypeError, ValueError):
        quantity, entry, lot_size = 0.0, 0.0, 1

    effective_quantity = quantity * lot_size
    holding = is_actual_holding(record)
    invested = entry * effective_quantity if holding else None
    current_value = (
        float(current_price) * effective_quantity
        if holding and current_price is not None and effective_quantity > 0
        else None
    )
    pnl = current_value - invested if current_value is not None and invested is not None else None
    pnl_pct = pnl / invested * 100 if pnl is not None and invested else None
    return {
        "is_holding": holding,
        "effective_quantity": effective_quantity,
        "invested": invested,
        "current_value": current_value,
        "pnl": pnl,
        "pnl_pct": pnl_pct,
    }
