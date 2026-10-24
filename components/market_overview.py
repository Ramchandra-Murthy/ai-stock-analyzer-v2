import streamlit as st

from services.market_service import get_market_indices, market_session_status


@st.cache_data(ttl=30, show_spinner=False)
def _get_cached_market_indices():
    """Refresh market observations at most once every 30 seconds."""
    return get_market_indices()


def _format_change(change):
    """Format a percentage change without assuming it is available."""
    if isinstance(change, (int, float)):
        return f"{change:+.2f}%"
    return None


def _show_market_status(items):
    """Show one clear freshness banner for the dashboard."""
    observations = [
        (info.get("observed_at"), info.get("frequency", "unknown"))
        for _name, info in items
        if info.get("observed_at")
    ]
    if not observations:
        st.warning("⚠️ MARKET DATA UNAVAILABLE — no observation timestamps were returned.")
        return

    latest_observed, latest_frequency = max(observations, key=lambda item: item[0])
    status = market_session_status(latest_observed, latest_frequency)

    if status["status"].startswith("INTRADAY DATA"):
        st.success(f"🟢 {status['status']} — {status['detail']}")
    elif status["status"] == "PRE-MARKET":
        st.info(f"🔵 {status['status']} — {status['detail']}")
    elif status["status"] == "DATA UNAVAILABLE":
        st.warning(f"⚠️ {status['status']} — {status['detail']}")
    else:
        st.warning(f"🟡 {status['status']} — {status['detail']}")

    st.caption(
        "Source: Yahoo Finance • Data is latest available, not exchange-tick live. "
        "Dashboard cache refreshes every 30 seconds."
    )


def show_market_overview():
    """
    Display major market indices with explicit data freshness.

    The canonical market service currently supplies latest available
    daily Yahoo Finance observations, not exchange-tick live prices.
    """
    st.subheader("🌍 Market Overview")

    data = _get_cached_market_indices()

    if not data:
        st.warning("Market data is currently unavailable.")
        return

    items = list(data.items())
    _show_market_status(items)

    # Show three readable index cards per row.
    for start in range(0, len(items), 3):
        row_items = items[start : start + 3]
        cols = st.columns(3)

        for col, (name, info) in zip(cols, row_items, strict=False):
            value = info.get("value")
            change = info.get("change")
            observed_at = info.get("observed_at")
            frequency = info.get("frequency", "unknown")
            is_tick_live = bool(info.get("is_tick_live", False))

            if value is None:
                col.metric(label=name, value="N/A")
            else:
                col.metric(
                    label=name,
                    value=value,
                    delta=_format_change(change),
                )

            if observed_at:
                freshness_label = "Tick live" if is_tick_live else f"Latest {frequency}"
                col.caption(f"{freshness_label} • {observed_at}")
            else:
                col.caption("Observation time unavailable")
