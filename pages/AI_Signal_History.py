"""Streamlit page for AI signal outcome history research."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ai_trading.signal_history import attach_horizon_outcomes, summarize_outcomes
from services.resilient_market_data import download_symbol_frames
from components.disclaimer import show_disclaimer

st.set_page_config(page_title="AI Signal History", page_icon="🗂️", layout="wide")

st.title("🗂️ AI Signal History")
show_disclaimer()
st.caption("Historical AI signal outcome analytics. No broker orders are submitted.")

records = st.session_state.get("ai_signal_records", [])
if isinstance(records, list) and records and st.button("Refresh completed signal outcomes"):
    tickers_by_key = {}
    for record in records:
        suffix = ".NS" if record.exchange == "NSE" else ".BO"
        ticker = (
            record.symbol
            if record.symbol.endswith((".NS", ".BO"))
            else f"{record.symbol}{suffix}"
        )
        tickers_by_key[f"{record.exchange}:{record.symbol}"] = ticker
    tickers = sorted(set(tickers_by_key.values()))
    with st.spinner(f"Checking {len(tickers)} symbols for completed outcomes..."):
        frames_by_ticker, diagnostics = download_symbol_frames(
            tickers,
            period="5y",
            interval="1d",
            auto_adjust=False,
            batch_size=10,
            timeout=15,
        )
        frames_by_key = {
            key: frames_by_ticker.get(ticker, pd.DataFrame())
            for key, ticker in tickers_by_key.items()
        }
        history = attach_horizon_outcomes(records, frames_by_key)
        st.session_state["ai_signal_history"] = history
    completed_count = int(history["completed"].sum()) if not history.empty else 0
    st.success(f"Updated signal outcomes: {completed_count}/{len(history)} horizons completed.")
    missing = diagnostics.get("missing", [])
    if missing:
        st.warning(f"Market data was unavailable for {len(missing)} symbols; those outcomes remain pending.")

history = st.session_state.get("ai_signal_history")

if not isinstance(history, pd.DataFrame):
    st.info(
        "No signal history has been recorded yet. Run the AI Trading Scanner "
        "and use its signal records to populate this research ledger."
    )
    st.stop()

st.subheader("Signal History")
st.dataframe(history, use_container_width=True, hide_index=True)

summary = summarize_outcomes(history)
if summary.empty:
    st.info("No completed signal outcomes are available yet.")
    st.stop()

st.subheader("Outcome Summary")
st.dataframe(summary, use_container_width=True, hide_index=True)

metric1, metric2, metric3 = st.columns(3)
completed = history[history["completed"]]
metric1.metric("Signals", len(history))
metric2.metric("Completed", len(completed))
metric3.metric(
    "Average completed return",
    f"{completed['return_pct'].mean():.2f}%" if not completed.empty else "N/A",
)

st.subheader("Completed Signal Returns")
st.bar_chart(
    completed.set_index("symbol")["return_pct"]
    if not completed.empty
    else history.set_index("symbol")["confidence_pct"]
)

csv = history.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download Signal History CSV",
    data=csv,
    file_name="ai_signal_history.csv",
    mime="text/csv",
)

st.caption(
    "Outcome returns are historical measurements based on supplied outcome prices. "
    "They are not forecasts or guarantees of future performance."
)
