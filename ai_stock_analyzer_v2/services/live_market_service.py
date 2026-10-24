"""Compatibility facade for the canonical market service.

The canonical service is the only yfinance boundary.  This module preserves
the older `price/change/percent` response shape for existing callers.
"""

from services.market_service import get_market_indices as _get_market_indices


def get_market_indices():
    """Return canonical observations in the legacy live-service shape."""
    result = {}

    for name, info in _get_market_indices().items():
        price = info.get("value")
        percent = info.get("change")

        absolute_change = None
        if price is not None and percent is not None:
            absolute_change = round(price * percent / 100, 2)

        result[name] = {
            "price": price,
            "change": absolute_change,
            "percent": percent,
            "observed_at": info.get("observed_at"),
            "source": info.get("source"),
            "frequency": info.get("frequency"),
            "is_intraday": info.get("is_intraday", False),
            "is_tick_live": info.get("is_tick_live", False),
        }

    return result
