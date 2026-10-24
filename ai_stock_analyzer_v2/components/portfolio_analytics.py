import streamlit as st


def show_portfolio_analytics(df):
    """
    Portfolio Analytics
    """

    if df.empty:
        st.info("No holdings available.")
        return

    valued = df.dropna(subset=["Return %"])
    if valued.empty:
        st.info("Live prices are unavailable, so performance analytics cannot be calculated yet.")
        return

    best = valued.loc[valued["Return %"].idxmax()]
    worst = valued.loc[valued["Return %"].idxmin()]

    # -----------------------------
    # Best & Worst Performer
    # -----------------------------

    st.metric("🏆 Best Performer", best["symbol"], f"{best['Return %']:.2f}%")

    st.metric("📉 Worst Performer", worst["symbol"], f"{worst['Return %']:.2f}%")

    st.divider()

    # -----------------------------
    # Portfolio Statistics
    # -----------------------------

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Average Return", f"{df['Return %'].mean():.2f}%")

    with col2:
        st.metric("Total Profit", f"₹{df['Profit'].sum():,.2f}")
