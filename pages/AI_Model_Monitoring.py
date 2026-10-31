"""Streamlit page for AI model monitoring and calibration."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ai_trading.calibration import evaluate_calibration, monitor_calibration_frames
from components.disclaimer import show_disclaimer
from scanner.universe import BSE_CANDIDATES, NSE_CANDIDATES
from services.cached_download import cached_download

st.set_page_config(
    page_title="AI Model Monitoring",
    page_icon="🎯",
    layout="wide",
)

st.title("🎯 AI Model Monitoring & Calibration")
show_disclaimer()
st.caption(
    "Measure whether ML probabilities are reliable on unseen historical data. "
    "No broker or live orders are submitted."
)

left, right = st.columns(2)
with left:
    exchange = st.selectbox("Exchange", ["NSE", "BSE"])
    universe = NSE_CANDIDATES if exchange == "NSE" else BSE_CANDIDATES
    symbol = st.selectbox("Monitoring symbol", universe[: min(30, len(universe))])
with right:
    horizon = st.slider("Forward horizon (days)", 1, 20, 5)
    threshold = st.slider("Positive-return threshold (%)", 0.0, 5.0, 1.0, 0.5)

bins = st.slider("Calibration bins", 2, 10, 5)

if st.button("Run Model Monitoring", type="primary"):
    ticker = (
        f"{str(symbol).strip().upper()}.NS"
        if exchange == "NSE"
        else f"{str(symbol).strip().upper()}.BO"
    )
    with st.spinner(f"Evaluating {ticker}..."):
        history = cached_download(
            ticker,
            period="5y",
            auto_adjust=False,
            progress=False,
            threads=False,
        )
        if isinstance(history.columns, pd.MultiIndex):
            history = history.droplevel(1, axis=1)

    try:
        metrics, calibration = evaluate_calibration(
            history,
            horizon=horizon,
            threshold=threshold / 100.0,
            bins=bins,
        )
    except (TypeError, ValueError, KeyError) as exc:
        st.error(f"Model monitoring could not run: {exc}")
        st.stop()

    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("Accuracy", f"{metrics.accuracy:.1%}")
    metric2.metric("Brier score", f"{metrics.brier_score:.3f}")
    metric3.metric("Calibration gap", f"{metrics.calibration_gap:.1%}")
    metric4.metric("Test samples", metrics.test_samples)

    st.subheader("Probability calibration")
    st.dataframe(calibration, use_container_width=True, hide_index=True)

    if not calibration.empty:
        chart = calibration.set_index("predicted_probability")[["actual_rate"]]
        st.line_chart(chart)

    st.subheader("Prediction distribution")
    st.write(
        f"Average predicted probability: **{metrics.average_probability:.1%}** · "
        f"Actual positive rate: **{metrics.actual_positive_rate:.1%}**"
    )

    st.caption(
        "Brier score measures probability error; lower is better. Calibration gap "
        "compares average predicted probability with the observed positive rate on "
        "the chronological holdout. These are historical measurements, not "
        "guarantees of future performance."
    )


st.divider()
st.subheader("Multi-stock calibration monitor")
st.caption(
    "Compare out-of-sample probability calibration across a selected stock universe. "
    "Lower Brier score and calibration gap indicate smaller historical probability error; "
    "these are not guarantees of future performance."
)

universe_count = st.slider("Universe symbols", 5, min(20, len(universe)), min(10, len(universe)), 5)
if st.button("Run Universe Monitoring"):
    selected = [str(symbol).strip().upper() for symbol in universe[:universe_count]]
    suffix = ".NS" if exchange == "NSE" else ".BO"
    tickers = [f"{symbol}{suffix}" for symbol in selected]
    with st.spinner(f"Evaluating {len(tickers)} {exchange} models..."):
        data = cached_download(
            tickers=tickers,
            period="5y",
            auto_adjust=False,
            progress=False,
            group_by="ticker",
            threads=False,
        )

    frames: dict[str, pd.DataFrame] = {}
    for symbol, ticker in zip(selected, tickers, strict=True):
        if isinstance(data.columns, pd.MultiIndex):
            if ticker not in data.columns.get_level_values(0):
                continue
            frame = data[ticker].copy()
        else:
            frame = data.copy()
        if not frame.empty and "Close" in frame.columns:
            frames[symbol] = frame.dropna(how="all")

    if not frames:
        st.warning("No usable historical data was returned for the selected universe.")
    else:
        monitor = monitor_calibration_frames(
            frames,
            exchange=exchange,
            horizon=horizon,
            threshold=threshold / 100.0,
            bins=bins,
        )
        if monitor.empty:
            st.warning("No symbols produced valid calibration metrics.")
        else:
            st.dataframe(monitor, use_container_width=True, hide_index=True)
            st.download_button(
                "Download calibration report",
                monitor.to_csv(index=False),
                file_name=f"{exchange.lower()}_ai_calibration_report.csv",
                mime="text/csv",
            )
