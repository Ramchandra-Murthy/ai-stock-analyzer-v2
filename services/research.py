import streamlit as st

from services.research_service import get_stock_profile


def format_number(value):
    """Format large numbers for display."""

    if value in [None, "N/A"]:
        return "N/A"

    try:
        value = float(value)

        if value >= 1_00_00_00_00_000:
            return f"₹{value/1_00_00_00_00_000:.2f} L Cr"

        elif value >= 1_00_00_00_000:
            return f"₹{value/1_00_00_00_000:.2f} Cr"

        elif value >= 1_00_000:
            return f"₹{value/1_00_000:.2f} L"

        return f"{value:,.2f}"

    except Exception:
        return str(value)


def show():

    st.title("🔍 Stock Research Terminal")
    st.markdown("---")

    col1, col2 = st.columns([3, 1])

    with col1:
        symbol = st.text_input(
            "Stock Symbol",
            value="RELIANCE",
            help="Enter NSE symbol like RELIANCE, TCS, INFY, SBIN",
        )

    with col2:
        st.write("")
        analyze = st.button("🔍 Analyze", use_container_width=True)

    if analyze:

        with st.spinner("Fetching company information..."):

            data = get_stock_profile(symbol)

        if data is None:

            st.error("Unable to fetch stock information.")
            return

        # ==========================================================
        # COMPANY PROFILE
        # ==========================================================

        st.subheader("🏢 Company Profile")

        c1, c2 = st.columns(2)

        with c1:

            st.metric("Company", data["company"])

            st.metric("Sector", data["sector"])

            st.metric("Industry", data["industry"])

            st.metric("Country", data["country"])

            st.metric("Employees", data["employees"])

        with c2:

            st.metric("Current Price", f'{data["price"]} {data["currency"]}')

            st.metric("Market Cap", format_number(data["market_cap"]))

            st.metric("Enterprise Value", format_number(data["enterprise_value"]))

            st.metric("Website", data["website"] if data["website"] else "N/A")

        st.divider()

        # ==========================================================
        # VALUATION
        # ==========================================================

        st.subheader("📊 Valuation")

        a, b, c, d, e = st.columns(5)

        a.metric("PE", data["pe"])

        b.metric("PB", data["pb"])

        c.metric("EPS", data["eps"])

        d.metric("Beta", data["beta"])

        e.metric("Dividend", data["dividend_yield"])

        st.divider()

        # ==========================================================
        # PROFITABILITY
        # ==========================================================

        st.subheader("📈 Profitability")

        p1, p2 = st.columns(2)

        p1.metric("ROE", data["roe"])

        p2.metric("Profit Margin", data["profit_margin"])

        st.divider()

        # ==========================================================
        # MARKET STATS
        # ==========================================================

        st.subheader("📉 Market Statistics")

        m1, m2, m3 = st.columns(3)

        m1.metric("52 Week High", data["high_52w"])

        m2.metric("52 Week Low", data["low_52w"])

        m3.metric("Average Volume", format_number(data["avg_volume"]))

        st.success("Research completed successfully.")
