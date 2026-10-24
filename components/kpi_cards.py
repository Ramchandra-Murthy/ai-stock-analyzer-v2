import streamlit as st

from components.metric_card import metric_card


def show_kpi_cards(summary):
    """
    Display portfolio KPI cards.
    """

    ai_score = summary.get("ai_score", 80)

    c1, c2, c3 = st.columns(3)

    with c1:
        metric_card("💰 Investment", f"₹{summary['investment']:,.2f}")

    with c2:
        metric_card("📈 Current Value", f"₹{summary['current_value']:,.2f}")

    with c3:
        metric_card("💵 Profit / Loss", f"₹{summary['profit']:,.2f}")

    st.write("")

    c4, c5, c6 = st.columns(3)

    with c4:
        metric_card("📊 Return", f"{summary['return']:.2f}%")

    with c5:
        metric_card("📁 Holdings", str(summary["holdings"]))

    with c6:
        metric_card("🤖 AI Score", f"{ai_score}/100")
