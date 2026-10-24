"""Compatibility facade for the canonical market service."""

from services.market_service import get_market_indices


def get_market_overview():
    """Return market overview using the canonical market-data boundary."""
    source = get_market_indices()
    return {
        name: {
            "value": info.get("value"),
            "change": (
                None
                if info.get("value") is None or info.get("change") is None
                else round(info["value"] * info["change"] / 100, 2)
            ),
            "percent": info.get("change"),
        }
        for name, info in source.items()
    }
