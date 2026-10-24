import streamlit as st

from services.market_service import get_market_indices, get_top_movers


def show_ai_market_summary():
    """
    Display a market-derived signal summary.

    This is intentionally deterministic: it uses the canonical market-data
    service and does not fabricate an AI confidence score or sector call.
    """

    st.subheader("🤖 Market Signal Summary")

    indices = get_market_indices()
    gainers, losers = get_top_movers()

    nifty_change = indices.get("NIFTY 50", {}).get("change")
    sensex_change = indices.get("SENSEX", {}).get("change")
    bank_nifty_change = indices.get("BANK NIFTY", {}).get("change")
    vix_value = indices.get("INDIA VIX", {}).get("value")

    valid_index_changes = [
        value
        for value in (nifty_change, sensex_change, bank_nifty_change)
        if isinstance(value, (int, float))
    ]

    if valid_index_changes:
        average_change = sum(valid_index_changes) / len(valid_index_changes)
        if average_change >= 0.50:
            trend = "Bullish"
        elif average_change <= -0.50:
            trend = "Bearish"
        else:
            trend = "Mixed / Sideways"
    else:
        average_change = None
        trend = "Unavailable"

    if isinstance(vix_value, (int, float)):
        if vix_value >= 20:
            risk = "Elevated"
        elif vix_value >= 15:
            risk = "Moderate"
        else:
            risk = "Lower"
    else:
        risk = "Unavailable"

    with st.container(border=True):
        st.metric(
            "Market Trend",
            trend,
            (f"{average_change:+.2f}% avg" if isinstance(average_change, (int, float)) else None),
        )

        st.metric(
            "India VIX",
            f"{vix_value:.2f}" if isinstance(vix_value, (int, float)) else "N/A",
            risk,
        )

        breadth_total = len(gainers) + len(losers)
        if breadth_total:
            st.metric(
                "Watchlist Breadth",
                f"{len(gainers)} gainers / {len(losers)} losers",
            )
        else:
            st.metric("Watchlist Breadth", "N/A")

        st.caption(
            "Derived from the latest available daily observations and the configured watchlist. "
            "It is a market signal, not an AI-generated forecast or live exchange-tick feed."
        )
