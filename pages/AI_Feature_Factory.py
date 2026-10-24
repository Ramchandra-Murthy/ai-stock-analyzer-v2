"""Streamlit dashboard for the standardized AI feature factory."""

# ruff: noqa: I001

from __future__ import annotations

import pandas as pd
import streamlit as st

from ai_trading.feature_factory import build_ai_feature_frame

st.set_page_config(page_title="AI Feature Factory", page_icon="🧩", layout="wide")
st.title("🧩 AI Feature Factory")
st.caption("Standardized research feature layer combining market, fundamental, and news inputs.")

st.subheader("Market Data")
close_values = st.text_area(
    "Close prices (comma-separated)",
    value="100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,"
    "116,117,118,119,120,121,122,123,124,125,126,127,128,129",
)
volume_values = st.text_area(
    "Volume (comma-separated)",
    value="1000,1010,1020,1030,1040,1050,1060,1070,1080,1090,1100,1110,1120,1130,"
    "1140,1150,1160,1170,1180,1190,1200,1210,1220,1230,1240,1250,1260,1270,1280,1290",
)

try:
    close = [float(value.strip()) for value in close_values.split(",") if value.strip()]
    volume = [float(value.strip()) for value in volume_values.split(",") if value.strip()]
    if len(close) != len(volume):
        raise ValueError("Close and Volume must contain the same number of values.")
    frame = pd.DataFrame({"Close": close, "Volume": volume})
    features = build_ai_feature_frame(frame, sentiment_score=0.0)
    st.metric("Feature Rows", len(features))
    st.dataframe(features.tail(10), use_container_width=True)
    st.download_button(
        "Download Feature CSV",
        features.to_csv(index=False).encode("utf-8"),
        "ai_feature_factory.csv",
        "text/csv",
    )
except ValueError as exc:
    st.error(str(exc))
