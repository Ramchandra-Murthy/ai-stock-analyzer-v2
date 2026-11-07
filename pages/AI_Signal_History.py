"""Streamlit page for AI signal outcome history research."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ai_trading.signal_history import attach_horizon_outcomes, summarize_outcomes
from ai_trading.signal_history_store import (
    SignalHistoryStoreError,
    load_signal_snapshot,
    save_signal_snapshot,
    signal_history_backend,
)
from ai_trading.signal_performance import summarize_signal_performance
from components.disclaimer import show_disclaimer
from services.resilient_market_data import download_symbol_frames

st.set_page_config(page_title="AI Signal History", page_icon="🗂️", layout="wide")

st.title("🗂️ AI Signal History")
show_disclaimer()
st.caption("Historical AI signal outcome analytics. No broker orders are submitted.")

if not st.session_state.get("ai_signal_store_loaded", False):
    try:
        stored_records, stored_history = load_signal_snapshot()
        st.session_state["ai_signal_records"] = stored_records
        st.session_state["ai_signal_history"] = stored_history
    except SignalHistoryStoreError as exc:
        st.warning(f"Persistent signal history is unavailable: {exc}")
        st.session_state.setdefault("ai_signal_records", [])
    st.session_state["ai_signal_store_loaded"] = True

st.caption(f"Signal history storage: {signal_history_backend().upper()}")
records = st.session_state.get("ai_signal_records", [])
if isinstance(records, list) and records and st.button("Refresh completed signal outcomes"):
    tickers_by_key = {}
    for record in records:
        suffix = ".NS" if record.exchange == "NSE" else ".BO"
        ticker = (
            record.symbol if record.symbol.endswith((".NS", ".BO")) else f"{record.symbol}{suffix}"
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
        try:
            save_signal_snapshot(records, history)
        except SignalHistoryStoreError as exc:
            st.warning(f"Outcomes were refreshed in this session but could not be persisted: {exc}")
    completed_count = int(history["completed"].sum()) if not history.empty else 0
    st.success(f"Updated signal outcomes: {completed_count}/{len(history)} horizons completed.")
    missing = diagnostics.get("missing", [])
    if missing:
        st.warning(
            f"Market data was unavailable for {len(missing)} symbols; those outcomes remain pending."
        )

history = st.session_state.get("ai_signal_history")

if not isinstance(history, pd.DataFrame) or history.empty:
    st.info(
        "No signal history has been recorded yet. Run the AI Trading Scanner "
        "and use its signal records to populate this research ledger."
    )
    st.stop()

# Backfill market movement for rows written before neutral signals were separated
# from directional strategy returns.
if "market_return_pct" not in history.columns:
    entry = pd.to_numeric(history.get("adjusted_entry_price"), errors="coerce")
    if entry is None:
        entry = pd.Series(float("nan"), index=history.index)
    entry = entry.fillna(pd.to_numeric(history.get("entry_price"), errors="coerce"))
    outcome = pd.to_numeric(history.get("outcome_price"), errors="coerce")
    history["market_return_pct"] = (outcome / entry - 1.0) * 100.0
neutral_mask = history["signal"].eq("NEUTRAL")
history.loc[neutral_mask, "return_pct"] = pd.NA

st.subheader("Signal History")
st.dataframe(history, use_container_width=True, hide_index=True)

summary = summarize_outcomes(history)
if summary.empty:
    st.info("No completed signal outcomes are available yet.")
else:
    st.subheader("Outcome Summary")
    st.dataframe(summary, use_container_width=True, hide_index=True)

st.subheader("Signal Performance & Reliability")
performance = summarize_signal_performance(history)
if performance.empty:
    st.info("Performance metrics require completed outcomes with valid returns.")
else:
    st.caption(
        "Only completed outcomes are included. Break-even results count in the sample, "
        "but are neither wins nor losses. Win-rate bounds are 95% Wilson intervals. "
        "Drawdown is an equally weighted sequential signal-return proxy, not account-level "
        "drawdown; overlapping positions, brokerage, taxes and slippage are not modeled."
    )
    st.dataframe(performance, use_container_width=True, hide_index=True)
    st.download_button(
        "Download Performance Report CSV",
        data=performance.to_csv(index=False).encode("utf-8"),
        file_name="signal_performance_report.csv",
        mime="text/csv",
    )

completed = history.loc[history["completed"].fillna(False)].copy()
directional = completed.loc[pd.to_numeric(completed["return_pct"], errors="coerce").notna()]
metric1, metric2, metric3 = st.columns(3)
metric1.metric("Signals", len(history))
metric2.metric("Completed outcomes", len(completed))
metric3.metric(
    "Average directional return",
    f"{directional['return_pct'].mean():.2f}%" if not directional.empty else "N/A",
)

neutral = completed.loc[completed["signal"].eq("NEUTRAL")]
if not neutral.empty and "market_return_pct" in neutral.columns:
    neutral_returns = pd.to_numeric(neutral["market_return_pct"], errors="coerce").dropna()
    if not neutral_returns.empty:
        st.info(
            f"Neutral signals are not treated as trades. Their underlying stocks averaged "
            f"{neutral_returns.mean():+.2f}% over the recorded horizon "
            f"({len(neutral_returns)} completed observations)."
        )

st.subheader("Completed Directional Signal Returns")
if directional.empty:
    st.info("Directional return charts will appear when completed LONG or SHORT outcomes exist.")
else:
    st.bar_chart(directional.set_index("symbol")["return_pct"])

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
