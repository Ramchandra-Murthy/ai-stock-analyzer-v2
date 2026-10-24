"""Streamlit dashboard for adaptive AI signal performance."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ai_trading.adaptive_performance import (
    adaptive_confidence_bucket_summary,
    adaptive_effect_summary,
    adaptive_performance_summary,
)

st.set_page_config(page_title="AI Adaptive Performance", page_icon="📊", layout="wide")

st.title("📊 AI Adaptive Signal Performance")
st.caption(
    "Historical monitoring of the adaptive AI confidence layer. " "No broker orders are submitted."
)

history = st.session_state.get("ai_signal_history")

if not isinstance(history, pd.DataFrame):
    st.info(
        "No AI signal history is available yet. Run the AI Trading Intelligence "
        "scanner and record signals first."
    )
    st.stop()

if "adaptive_confidence_pct" not in history.columns:
    st.info(
        "Adaptive confidence metadata is not present in this signal history. "
        "Record new signals after the adaptive scanner integration is active."
    )
    st.stop()

effect = adaptive_effect_summary(history)
completed = int(effect["completed"])

metric1, metric2, metric3, metric4, metric5 = st.columns(5)
metric1.metric("Completed signals", completed)
metric2.metric("Raw confidence", f"{effect['average_raw_confidence_pct']:.1f}%")
metric3.metric(
    "Adaptive confidence",
    f"{effect['average_adaptive_confidence_pct']:.1f}%",
)
metric4.metric(
    "Average adjustment",
    f"{effect['average_adjustment_pct']:+.1f}%",
)
metric5.metric("Win rate", f"{effect['win_rate_pct']:.1f}%")

st.subheader("Performance by signal")
signal_summary = adaptive_performance_summary(history, group_by="signal")
if signal_summary.empty:
    st.info("No completed adaptive signal outcomes are available yet.")
else:
    st.dataframe(signal_summary, use_container_width=True, hide_index=True)

st.subheader("Performance by market regime")
regime_summary = adaptive_performance_summary(history, group_by="regime")
if regime_summary.empty:
    st.info("No completed regime-tagged adaptive outcomes are available yet.")
else:
    st.dataframe(regime_summary, use_container_width=True, hide_index=True)

st.subheader("Performance by adaptive confidence bucket")
bucket_summary = adaptive_confidence_bucket_summary(history)
if bucket_summary.empty:
    st.info("No completed adaptive confidence outcomes are available yet.")
else:
    st.dataframe(bucket_summary, use_container_width=True, hide_index=True)

chart_left, chart_right = st.columns(2)
with chart_left:
    st.subheader("Raw vs adaptive confidence")
    if not history[history["completed"]].empty:
        completed_history = history[history["completed"]].copy()
        chart_data = completed_history[
            ["symbol", "confidence_pct", "adaptive_confidence_pct"]
        ].set_index("symbol")
        st.bar_chart(chart_data.head(20))

with chart_right:
    st.subheader("Adaptive adjustment by signal")
    if not signal_summary.empty:
        st.bar_chart(signal_summary.set_index("group")["avg_adaptive_adjustment_pct"])

st.subheader("Adaptive signal records")
display_columns = [
    column
    for column in [
        "timestamp",
        "symbol",
        "signal",
        "regime",
        "confidence_pct",
        "adaptive_confidence_pct",
        "adaptive_adjustment_pct",
        "adaptive_samples",
        "return_pct",
        "completed",
    ]
    if column in history.columns
]
st.dataframe(
    history[display_columns].tail(100),
    use_container_width=True,
    hide_index=True,
)

st.download_button(
    "Download adaptive performance CSV",
    data=history.to_csv(index=False).encode("utf-8"),
    file_name="ai_adaptive_signal_performance.csv",
    mime="text/csv",
)

st.caption(
    "All measurements are historical observations from completed signal outcomes. "
    "They are intended for calibration and research, not as guarantees of future returns."
)
