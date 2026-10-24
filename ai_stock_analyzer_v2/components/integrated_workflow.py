"""Streamlit presentation helpers for the integrated Chapter 4-10 workflow."""

from __future__ import annotations

import pandas as pd
import streamlit as st


def show_integrated_workflow(frame: pd.DataFrame) -> None:
    """Render the latest integrated trading snapshot and recent bars."""
    if frame.empty:
        st.info("No integrated workflow data is available.")
        return

    latest = frame.iloc[-1]
    st.subheader("Chapter 4-10 Trading Workflow")
    cols = st.columns(4)
    cols[0].metric("Regime", str(latest["regime"]))
    cols[1].metric("Regime Score", f"{float(latest['regime_score']):.1f}")
    cols[2].metric("Edge Signal", f"{float(latest['edge_signal']):.1f}")
    cols[3].metric("Close", f"{float(latest['close']):,.2f}")
    display = frame.tail(20).copy()
    display["close"] = display["close"].round(2)
    display["regime_score"] = display["regime_score"].round(2)
    st.dataframe(display, use_container_width=True)


def show_live_integrated_scanner(frame: pd.DataFrame) -> None:
    """Render the latest multi-symbol integrated scanner output."""
    st.subheader("Live Integrated Trading Scanner")
    if frame.empty:
        st.info("No integrated scanner data is available.")
        return
    display = frame.copy()
    for column in ("Close", "Regime Score", "Edge Signal", "Change %"):
        if column in display:
            display[column] = display[column].round(2)
    st.dataframe(display, use_container_width=True, hide_index=True)
