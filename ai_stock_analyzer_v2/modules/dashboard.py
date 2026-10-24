import streamlit as st

from components.add_holding_form import show_add_holding_form
from components.ai_market_summary import show_ai_market_summary
from components.ai_score import show_ai_score
from components.edit_holding_form import show_edit_holding_form
from components.export_portfolio import export_portfolio
from components.investment_chart import show_investment_chart
from components.kpi_cards import show_kpi_cards
from components.market_movers import show_market_movers
from components.market_overview import show_market_overview
from components.performance_chart import show_performance_chart
from components.portfolio_allocation import show_portfolio_allocation
from components.portfolio_analytics import show_portfolio_analytics
from components.quick_actions import show_quick_actions
from components.top_holdings import show_top_holdings
from services.portfolio_service import get_portfolio, get_summary


def calculate_ai_score(summary):

    score = 100

    if summary["holdings"] < 5:
        score -= 20

    if summary["return"] < 0:
        score -= 10

    if summary["investment"] == 0:
        score = 0

    return max(score, 0)


def show():

    st.title("📈 AI Stock Analyzer Pro")
    st.caption("Professional Portfolio Dashboard")
    show_market_overview()

    st.divider()

    df = get_portfolio()
    summary = get_summary(df)

    summary["ai_score"] = calculate_ai_score(summary)

    # ============================
    # KPI CARDS
    # ============================

    show_kpi_cards(summary)

    st.divider()

    # ============================
    # ROW 1
    # ============================

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📈 Portfolio Performance")
        show_performance_chart(df)

    with col2:
        st.subheader("🤖 AI Portfolio Health")
        show_ai_score(summary["ai_score"])

    st.divider()

    # ============================
    # ROW 2
    # ============================

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🥧 Portfolio Allocation")
        show_portfolio_allocation(df)

    with col2:
        st.subheader("💰 Investment vs Current Value")
        show_investment_chart(df)

    st.divider()

    # ============================
    # ROW 3 — FULL-WIDTH SECTIONS
    # ============================

    st.subheader("📋 Top Holdings")
    show_top_holdings(df)

    st.divider()

    # Market-wide scans make multiple external requests. Run them on demand so the
    # portfolio dashboard can render without waiting for every quote provider.
    with st.expander("🔥 Market Movers (load on demand)", expanded=False):
        if st.button("Load market movers", key="load_dashboard_market_movers"):
            st.session_state["dashboard_market_movers_requested"] = True
        if st.session_state.get("dashboard_market_movers_requested", False):
            with st.spinner("Loading market movers from available data providers…"):
                show_market_movers()
        else:
            st.caption("Select Load market movers to fetch the latest available quotes.")

    st.divider()

    with st.expander("🤖 Market Signal Summary (load on demand)", expanded=False):
        if st.button("Load market signal summary", key="load_dashboard_market_summary"):
            st.session_state["dashboard_market_summary_requested"] = True
        if st.session_state.get("dashboard_market_summary_requested", False):
            with st.spinner("Loading market observations…"):
                show_ai_market_summary()
        else:
            st.caption("Market signal data is fetched only when requested.")

    st.divider()

    st.subheader("📊 Portfolio Analytics")
    show_portfolio_analytics(df)

    st.divider()

    # ============================
    # QUICK ACTIONS
    # ============================

    st.subheader("⚡ Quick Actions")

    c1, c2 = st.columns([1, 1])

    with c1:
        show_quick_actions()

    with c2:
        export_portfolio(df)

    st.divider()

    # ============================
    # ADD / EDIT HOLDINGS
    # ============================

    with st.expander("➕ Add New Holding", expanded=False):
        show_add_holding_form()

    with st.expander("✏️ Edit Holding", expanded=False):
        show_edit_holding_form(df)
