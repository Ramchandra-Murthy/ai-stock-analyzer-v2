import streamlit as st

from charts.candlestick import create_candlestick
from portfolio.portfolio import add_stock, create_portfolio_table, load_portfolio
from scanner.market_scanner import market_scan
from services.analyzer import analyze_stock

# ====================================================
# PAGE CONFIG
# ====================================================

st.set_page_config(page_title="AI Stock Analyzer Pro", page_icon="📈", layout="wide")

create_portfolio_table()

# ====================================================
# SIDEBAR
# ====================================================

st.sidebar.title("📊 Dashboard")

st.sidebar.header("Portfolio")

portfolio_symbol = st.sidebar.text_input("Symbol", "RELIANCE.NS")

portfolio_qty = st.sidebar.number_input("Quantity", min_value=1, value=10)

portfolio_price = st.sidebar.number_input("Buy Price", min_value=0.0, value=1000.0, step=1.0)

if st.sidebar.button("➕ Add To Portfolio"):

    add_stock(portfolio_symbol, portfolio_qty, portfolio_price)

    st.sidebar.success("Added Successfully")

st.sidebar.divider()

period = st.sidebar.selectbox("History", ["3mo", "6mo", "1y", "2y", "5y"], index=2)

interval = st.sidebar.selectbox("Interval", ["1d", "1wk", "1mo"], index=0)

# ====================================================
# MAIN TITLE
# ====================================================

st.title("📈 AI Stock Analyzer Pro")

symbol = st.text_input("Stock Symbol", "RELIANCE.NS")

# ====================================================
# ANALYZE
# ====================================================

if st.button("Analyze"):

    with st.spinner("Downloading market data..."):

        result = analyze_stock(symbol)

    last = result["last"]
    trend = result["trend"]
    signal = result["signal"]
    breakout = result["breakout"]

    st.success("Analysis Complete")

    # ==========================
    # TOP METRICS
    # ==========================

    col1, col2, col3 = st.columns(3)

    col1.metric("Current Price", f"₹{last['Close']:.2f}")

    col2.metric("Trend", trend["Trend"])

    col3.metric("Recommendation", signal["Recommendation"])

    # ==========================
    # TECHNICAL INDICATORS
    # ==========================

    st.divider()

    st.subheader("📊 Technical Indicators")

    c1, c2, c3 = st.columns(3)

    c1.metric("RSI", f"{last['RSI_14']:.2f}")
    c1.metric("ATR", f"{last['ATR']:.2f}")

    c2.metric("MACD", f"{last['MACD']:.2f}")
    c2.metric("Signal", f"{last['Signal']:.2f}")

    c3.metric("Support", f"{last['Support']:.2f}")
    c3.metric("Resistance", f"{last['Resistance']:.2f}")

    # ==========================
    # AI SIGNAL
    # ==========================

    st.divider()

    st.subheader("🤖 AI Signal Engine")

    score_col, rec_col = st.columns(2)

    score_col.metric("AI Score", signal["Score"])

    rec = signal["Recommendation"]

    if rec == "BUY":
        rec_col.success(rec)
    elif rec == "SELL":
        rec_col.error(rec)
    else:
        rec_col.warning(rec)

    st.write("### Reasons")

    for reason in signal["Reasons"]:
        st.write(f"✅ {reason}")

    # ==========================
    # BREAKOUT
    # ==========================

    st.divider()

    st.subheader("🚀 Breakout Engine")

    if breakout["Signal"] == "BUY":
        st.success(breakout["Signal"])
    elif breakout["Signal"] == "SELL":
        st.error(breakout["Signal"])
    else:
        st.info(breakout["Signal"])

    st.write(breakout["Reason"])

    # ==========================
    # CHART
    # ==========================

    st.divider()

    st.subheader("📈 Technical Chart")

    fig = create_candlestick(result["df"], symbol)

    st.plotly_chart(fig, use_container_width=True)

    # ==========================
    # DATA TABLE
    # ==========================

    st.divider()

    st.subheader("📄 Latest Market Data")

    st.dataframe(result["df"].tail(20), use_container_width=True, hide_index=True)

# ====================================================
# PORTFOLIO
# ====================================================

st.divider()

st.header("💼 My Portfolio")

portfolio = load_portfolio()

if portfolio.empty:

    st.info("Portfolio is empty.")

else:

    st.dataframe(portfolio, use_container_width=True, hide_index=True)

# ====================================================
# NIFTY SCANNER
# ====================================================

st.divider()

st.header("📈 NIFTY Scanner")

buy_only = st.checkbox("Show BUY Only")

if st.button("🔍 Scan Market"):

    with st.spinner("Scanning NIFTY Stocks..."):

        scan = market_scan()

    if not scan.empty:

        scan = scan.sort_values("Score", ascending=False)

        if buy_only:

            scan = scan[scan["Signal"] == "BUY"]

        st.dataframe(scan, use_container_width=True, hide_index=True)

    else:

        st.warning("No stocks found.")

else:

    st.info("Click 'Scan Market' to scan NIFTY stocks.")
