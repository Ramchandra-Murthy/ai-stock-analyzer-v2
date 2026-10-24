import pandas as pd
import plotly.express as px
import streamlit as st


def show_performance_chart(df):
    """
    Portfolio Performance Chart
    """

    if df.empty:
        st.info("No holdings available.")
        return

    chart_df = df.copy()
    # Holdings without a live price have no profit figure; plot only valued holdings.
    chart_df["Profit"] = pd.to_numeric(chart_df["Profit"], errors="coerce")
    chart_df = chart_df.dropna(subset=["Profit"])
    if chart_df.empty:
        st.info("Live prices are unavailable, so holding performance cannot be charted yet.")
        return

    chart_df["Status"] = chart_df["Profit"].apply(lambda x: "Profit" if x >= 0 else "Loss")

    fig = px.bar(
        chart_df,
        x="symbol",
        y="Profit",
        color="Status",
        text="Profit",
        color_discrete_map={"Profit": "#2ECC71", "Loss": "#E74C3C"},
    )

    fig.update_traces(texttemplate="₹%{text:,.0f}", textposition="outside")

    fig.update_layout(
        height=420,
        showlegend=False,
        xaxis_title="Stock",
        yaxis_title="Profit / Loss (₹)",
        margin={"l": 20, "r": 20, "t": 20, "b": 20},
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
