import plotly.graph_objects as go
import streamlit as st


def show_portfolio_chart(summary):
    """
    Display Investment vs Current Value chart.

    Parameters
    ----------
    summary : dict
        Dictionary returned by portfolio_summary()
    """

    investment = summary["investment"]
    current_value = summary["current_value"]

    fig = go.Figure()

    fig.add_trace(go.Bar(name="Investment", x=["Portfolio"], y=[investment]))

    fig.add_trace(go.Bar(name="Current Value", x=["Portfolio"], y=[current_value]))

    fig.update_layout(
        title="📈 Portfolio Value Comparison",
        barmode="group",
        height=450,
        template="plotly_white",
        xaxis_title="",
        yaxis_title="Value (₹)",
    )

    st.plotly_chart(fig, use_container_width=True)
