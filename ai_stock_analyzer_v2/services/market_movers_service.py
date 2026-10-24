"""Compatibility facade for market movers.

All market price retrieval is delegated to the canonical market service so
the application cannot silently use a second definition of "current" data.
"""

from services.market_service import get_top_movers


def get_market_movers():
    """Return gainers and losers using the canonical market service."""
    gainers, losers = get_top_movers()

    def records(frame):
        return [
            {
                "Stock": row["Symbol"],
                "Price": row["Price"],
                "% Change": row["Change %"],
            }
            for _, row in frame.iterrows()
        ]

    return records(gainers), records(losers)
