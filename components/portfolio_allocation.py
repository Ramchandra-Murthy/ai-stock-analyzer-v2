import plotly.express as px
import streamlit as st


def show_portfolio_allocation(df):
    """
    Display portfolio allocation donut chart.
    """

    if df.empty:
        st.info("No holdings available.")
        return

    if "Current Value" not in df.columns:
        st.warning("Current Value column not found.")
        return

    chart_df = df.copy()

    chart_df["Current Value"] = chart_df["Current Value"].fillna(0)

    fig = px.pie(chart_df, names="symbol", values="Current Value", hole=0.55)

    fig.update_traces(textposition="inside", textinfo="percent+label")

    fig.update_layout(height=420, margin={"l": 20, "r": 20, "t": 20, "b": 20}, showlegend=True)

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
