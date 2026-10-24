"""Streamlit dashboard for the chronological adaptive-learning loop."""

# ruff: noqa: I001

from __future__ import annotations

import pandas as pd
import streamlit as st

from ai_trading.learning_loop import learning_loop_summary, run_learning_loop

st.set_page_config(page_title="AI Adaptive Learning", page_icon="🔄", layout="wide")
st.title("🔄 AI Adaptive Learning Loop")
st.caption(
    "Chronological research monitor: each signal is evaluated using only completed "
    "outcomes available before its timestamp. No live orders are placed."
)

history = st.session_state.get("ai_signal_history")
if not isinstance(history, pd.DataFrame) or history.empty:
    st.info("Run the AI Trading Scanner and record signals before using this monitor.")
    st.stop()

with st.sidebar:
    min_samples = st.slider("Minimum learning samples", 2, 50, 10)
    max_adjustment = st.slider("Maximum confidence adjustment %", 1.0, 20.0, 10.0)

replay = run_learning_loop(
    history,
    min_samples=min_samples,
    max_adjustment_pct=max_adjustment,
)
summary = learning_loop_summary(replay)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Signals", int(summary["signals"]))
col2.metric("Completed", int(summary["completed"]))
col3.metric("Learned Signals", int(summary["learned_signals"]))
col4.metric("Max Adjustment", f"{summary['maximum_adjustment_pct']:.1f}%")

st.subheader("Chronological Learning Replay")
st.dataframe(replay, use_container_width=True)

if not replay.empty:
    st.subheader("Adaptive Confidence")
    chart = replay.set_index("timestamp")[["raw_confidence_pct", "adaptive_confidence_pct"]]
    st.line_chart(chart)

    st.subheader("Learning Adjustments")
    st.bar_chart(replay.set_index("timestamp")["adaptive_adjustment_pct"])

st.download_button(
    "Download Learning Replay CSV",
    replay.to_csv(index=False).encode("utf-8"),
    "ai_adaptive_learning_replay.csv",
    "text/csv",
)
