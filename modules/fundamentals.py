import streamlit as st

from services.fundamental_score_service import calculate_fundamental_score
from services.research_service import get_stock_profile
from services.ui_formatters import (
    format_debt_to_equity,
    format_large_rupees,
    format_market_cap,
    format_percent,
    format_price,
    format_ratio,
)


def _display_value(value):
    """Return a readable value for missing or unavailable company data."""
    if value is None or value == "":
        return "N/A"
    return value


def show():
    st.title("📊 Fundamentals")
    st.caption("Company financial metrics and a data-based fundamental score")

    with st.form("fundamentals_lookup_form"):
        symbol_input = st.text_input(
            "Enter NSE symbol",
            value=st.session_state.get("fundamentals_symbol", "RELIANCE"),
            help="Enter a ticker such as RELIANCE, TCS, or HDFCBANK. NSE suffix is added automatically.",
        )
        submitted = st.form_submit_button("Analyze", use_container_width=True)

    if submitted:
        symbol = symbol_input.strip().upper()
        if not symbol:
            st.warning("Enter an NSE symbol to continue.")
            return
        st.session_state["fundamentals_symbol"] = symbol
        st.session_state["fundamentals_result_symbol"] = symbol

    symbol = st.session_state.get("fundamentals_result_symbol")
    if not symbol:
        st.info("Enter an NSE symbol above and select Analyze.")
        return

    try:
        with st.spinner(f"Loading financial data for {symbol}…"):
            data = get_stock_profile(symbol)
    except Exception as error:
        st.error(f"Could not load financial data for {symbol}: {error}")
        return

    if not isinstance(data, dict) or not data:
        st.error(f"No financial profile was returned for {symbol}.")
        return

    company = data.get("company") or symbol
    st.subheader(f"{company} ({symbol})")
    st.caption(
        "Financial information is sourced from Yahoo Finance and may be incomplete or delayed. "
        "This page is informational, not investment advice."
    )

    try:
        score, reasons = calculate_fundamental_score(data)
    except Exception as error:
        score, reasons = None, [f"Fundamental score unavailable: {error}"]

    score_col, price_col, cap_col = st.columns(3)
    with score_col:
        st.metric("Fundamental score", f"{score}/100" if score is not None else "N/A")
    with price_col:
        st.metric("Latest available price", format_price(data.get("price")))
    with cap_col:
        st.metric("Market capitalization", format_market_cap(data.get("market_cap")))

    if score is None:
        st.warning("There is not enough reliable fundamental data to calculate a score.")
    elif score >= 75:
        st.success("The available metrics indicate a relatively strong fundamental score.")
    elif score >= 50:
        st.info("The available metrics indicate a mixed or moderate fundamental score.")
    else:
        st.warning("The available metrics indicate a relatively weak fundamental score.")

    st.subheader("Valuation")
    valuation_cols = st.columns(3)
    valuation_metrics = (
        ("Trailing P/E", data.get("pe")),
        ("Forward P/E", data.get("forward_pe")),
        ("Price / Book", data.get("pb")),
        ("EPS", data.get("eps")),
        ("Forward EPS", data.get("forward_eps")),
        ("Dividend yield", format_percent(data.get("dividend_yield"))),
    )
    for index, (label, value) in enumerate(valuation_metrics):
        with valuation_cols[index % len(valuation_cols)]:
            st.metric(label, _display_value(value) if label != "Dividend yield" else value)

    st.subheader("Profitability and growth")
    profitability_cols = st.columns(3)
    profitability_metrics = (
        ("Return on equity", format_percent(data.get("roe"))),
        ("Return on assets", format_percent(data.get("roa"))),
        ("Net profit margin", format_percent(data.get("profit_margin"))),
        ("Operating margin", format_percent(data.get("operating_margin"))),
        ("Revenue growth", format_percent(data.get("revenue_growth"))),
        ("Earnings growth", format_percent(data.get("earnings_growth"))),
    )
    for index, (label, value) in enumerate(profitability_metrics):
        with profitability_cols[index % len(profitability_cols)]:
            st.metric(label, value)

    st.subheader("Financial health")
    health_cols = st.columns(3)
    health_metrics = (
        ("Debt / equity", format_debt_to_equity(data.get("debt_to_equity"))),
        ("Current ratio", format_ratio(data.get("current_ratio"))),
        ("Total debt", format_large_rupees(data.get("total_debt"))),
        ("Total cash", format_large_rupees(data.get("total_cash"))),
        ("Operating cash flow", format_large_rupees(data.get("operating_cash_flow"))),
        ("Free cash flow", format_large_rupees(data.get("free_cash_flow"))),
    )
    for index, (label, value) in enumerate(health_metrics):
        with health_cols[index % len(health_cols)]:
            st.metric(label, value)

    with st.expander("How the score was assessed", expanded=True):
        if reasons:
            for reason in reasons:
                st.write(f"- {reason}")
        else:
            st.write("No scoring details are available.")

    observed_at = data.get("quote_timestamp")
    source = data.get("price_source") or "Unknown"
    frequency = data.get("quote_frequency") or "Unknown"
    st.caption(
        f"Price source: {source} · Frequency: {frequency} · "
        f"Observed at: {observed_at or 'not provided'}"
    )
