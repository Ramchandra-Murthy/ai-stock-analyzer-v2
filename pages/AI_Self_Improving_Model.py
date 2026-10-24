"""Streamlit dashboard for AI model retraining readiness."""

# ruff: noqa: I001

from __future__ import annotations

import pandas as pd
import streamlit as st

from ai_trading.self_improving import evaluate_retraining_need

st.set_page_config(page_title="AI Self-Improving Model", page_icon="🧠", layout="wide")
st.title("🧠 AI Self-Improving Model Engine")
st.caption(
    "Historical research monitor: evaluates whether accumulated completed outcomes "
    "justify model retraining. It does not retrain or place live orders."
)

history = st.session_state.get("ai_signal_history")
if not isinstance(history, pd.DataFrame) or history.empty:
    st.info("Run the AI Trading Scanner and record signals before using this monitor.")
    st.stop()

with st.sidebar:
    min_samples = st.slider("Minimum completed samples", 10, 200, 30)
    lookback = st.slider("Recent outcome window", 10, 100, 30)
    min_win_rate = st.slider("Minimum recent win rate %", 0.0, 100.0, 50.0)
    max_gap = st.slider("Maximum confidence gap %", 0.0, 50.0, 15.0)

decision = evaluate_retraining_need(
    history,
    min_samples=min_samples,
    lookback=lookback,
    min_win_rate_pct=min_win_rate,
    max_confidence_gap_pct=max_gap,
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Retraining", "DUE" if decision.should_retrain else "NOT DUE")
col2.metric("Completed Samples", decision.completed_samples)
col3.metric("Recent Win Rate", f"{decision.recent_win_rate_pct:.1f}%")
col4.metric("Avg Confidence", f"{decision.recent_avg_confidence_pct:.1f}%")

st.subheader("Model Readiness")
st.info(decision.reason)

st.subheader("Recent Evidence")
st.dataframe(
    history[history["completed"]].tail(lookback),
    use_container_width=True,
)
