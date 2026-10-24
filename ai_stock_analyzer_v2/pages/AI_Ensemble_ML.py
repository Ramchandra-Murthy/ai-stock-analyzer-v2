"""Streamlit dashboard for ensemble AI model research."""

# ruff: noqa: I001

from __future__ import annotations

import pandas as pd
import streamlit as st

from ai_trading.ensemble_model import train_ensemble

st.set_page_config(page_title="AI Ensemble ML", page_icon="🤖", layout="wide")
st.title("🤖 AI Ensemble ML Engine")
st.caption("Research monitor: chronological ensemble validation. No live orders are placed.")

symbol = st.text_input("Symbol label", value="RESEARCH")
horizon = st.slider("Prediction horizon", 1, 20, 5)
threshold = st.number_input("Minimum future return %", value=0.0, step=0.5)
close_text = st.text_area(
    "Close prices (comma-separated)",
    value=",".join(str(100 + i + (i % 7) * 0.5) for i in range(120)),
)
volume_text = st.text_area(
    "Volume (comma-separated)",
    value=",".join(str(1000 + i * 10) for i in range(120)),
)

try:
    close = [float(value.strip()) for value in close_text.split(",") if value.strip()]
    volume = [float(value.strip()) for value in volume_text.split(",") if value.strip()]
    if len(close) != len(volume):
        raise ValueError("Close and Volume must contain the same number of values.")
    frame = pd.DataFrame({"Close": close, "Volume": volume})
    if st.button("Run Ensemble Validation"):
        models, validation = train_ensemble(
            frame,
            horizon=horizon,
            threshold=threshold / 100.0,
        )
        col1, col2, col3 = st.columns(3)
        col1.metric("Validation Accuracy", f"{validation.accuracy:.1%}")
        col2.metric(
            "ROC-AUC",
            "N/A" if validation.roc_auc is None else f"{validation.roc_auc:.3f}",
        )
        col3.metric("Validation Samples", validation.test_samples)
        st.success(f"{symbol}: ensemble validation completed.")
except ValueError as exc:
    st.error(str(exc))
