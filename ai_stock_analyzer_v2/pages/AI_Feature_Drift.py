"""AI feature drift monitoring dashboard."""

# ruff: noqa: I001

from __future__ import annotations

import pandas as pd
import streamlit as st

from ai_trading.feature_drift import build_feature_drift_report

st.title("AI Feature Drift")
st.caption("Research monitor for changes between baseline and recent feature distributions.")

baseline_text = st.text_area("Baseline Close prices", height=120)
baseline_volume = st.text_area("Baseline Volumes", height=120)
current_text = st.text_area("Current Close prices", height=120)
current_volume = st.text_area("Current Volumes", height=120)
threshold = st.slider("Drift threshold (standard deviations)", 0.5, 5.0, 2.0, 0.1)


def _parse(values: str) -> list[float]:
    return [float(value.strip()) for value in values.split(",") if value.strip()]


if st.button("Run Feature Drift"):
    try:
        baseline_close = _parse(baseline_text)
        baseline_vol = _parse(baseline_volume)
        current_close = _parse(current_text)
        current_vol = _parse(current_volume)
        if len(baseline_close) != len(baseline_vol) or len(current_close) != len(current_vol):
            raise ValueError("Close and volume lengths must match")
        baseline = pd.DataFrame({"Close": baseline_close, "Volume": baseline_vol})
        current = pd.DataFrame({"Close": current_close, "Volume": current_vol})
        report = build_feature_drift_report(
            baseline,
            current,
            threshold=threshold,
        )
        st.metric("Features checked", len(report))
        drifted_count = int(report["drifted"].sum()) if not report.empty else 0
        st.metric("Drifted features", drifted_count)
        if report.empty:
            st.info(
                "No feature distributions are available for comparison yet. "
                "Provide baseline and current Close/Volume data, then run the drift check."
            )
        else:
            st.dataframe(report, use_container_width=True)
    except ValueError as exc:
        st.error(str(exc))
