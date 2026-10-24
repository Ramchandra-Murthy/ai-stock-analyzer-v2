import plotly.graph_objects as go
import streamlit as st


def show_investment_chart(df):
    """
    Compare invested amount with current value for each holding.
    """

    if df.empty:
        st.info("No holdings available.")
        return

    invested = df["quantity"] * df["buy_price"]

    fig = go.Figure()

    fig.add_bar(name="Investment", x=df["symbol"], y=invested)

    fig.add_bar(name="Current Value", x=df["symbol"], y=df["Current Value"])

    fig.update_layout(barmode="group", height=500, xaxis_title="Stock", yaxis_title="Amount (₹)")

    st.plotly_chart(fig, use_container_width=True)
