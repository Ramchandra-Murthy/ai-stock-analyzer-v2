from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st

from portfolio.portfolio import (
    add_stock,
    create_portfolio_table,
    delete_stock,
)

# ----------------------------------------------------------
# PORTFOLIO DATA
# ----------------------------------------------------------
from services.portfolio_service import get_portfolio

# ----------------------------------------------------------
# PORTFOLIO PAGE
# ----------------------------------------------------------


def show():

    st.title("💼 Portfolio Manager")

    create_portfolio_table()
    # ======================================================
    # ADD STOCK
    # ======================================================

    st.subheader("➕ Add Stock")

    col1, col2, col3 = st.columns(3)

    with col1:
        symbol = st.text_input("Stock Symbol", placeholder="RELIANCE.NS")

    with col2:
        quantity = st.number_input("Quantity", min_value=1, value=1)

    with col3:
        buy_price = st.number_input("Buy Price (₹)", min_value=0.0, value=100.0)

    if st.button("Add Stock", key="add_stock"):

        if symbol.strip() == "":
            st.error("Please enter a stock symbol.")

        else:
            add_stock(symbol.strip().upper(), quantity, buy_price)

            st.success("Stock Added Successfully")
            st.rerun()

    st.divider()

    # ======================================================
    # LOAD + VALUE DATA
    # ======================================================

    df = get_portfolio()

    if df.empty:
        st.info("Your portfolio is empty.")
        return

    st.caption(
        "Portfolio prices are the latest available daily observations from Yahoo Finance; "
        "they are not exchange-tick live prices."
    )

    # ======================================================
    # SUMMARY
    # ======================================================

    total_cost = (df["quantity"] * df["buy_price"]).sum()
    total_value = df["Current Value"].fillna(0).sum()
    total_profit = total_value - total_cost

    total_return = (total_profit / total_cost) * 100 if total_cost > 0 else 0

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("💰 Investment", f"₹{total_cost:,.2f}")
    c2.metric("📈 Current Value", f"₹{total_value:,.2f}")
    c3.metric("💵 Profit/Loss", f"₹{total_profit:,.2f}")
    c4.metric("📊 Return", f"{total_return:.2f}%")

    st.divider()

    # ======================================================
    # ANALYTICS
    # ======================================================

    st.subheader("📊 Portfolio Analytics")

    valid = df.dropna(subset=["Return %"])

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Holdings", len(df))

    if not valid.empty:

        best = valid.loc[valid["Return %"].idxmax()]
        worst = valid.loc[valid["Return %"].idxmin()]

        c2.metric("Best", best["symbol"], f"{best['Return %']:.2f}%")

        c3.metric("Worst", worst["symbol"], f"{worst['Return %']:.2f}%")

        c4.metric("Average", f"{valid['Return %'].mean():.2f}%")

    st.divider()

    # ======================================================
    # HOLDINGS
    # ======================================================

    st.subheader("📋 Portfolio Holdings")

    display_df = df.rename(
        columns={
            "id": "ID",
            "symbol": "Symbol",
            "quantity": "Quantity",
            "buy_price": "Buy Price",
        }
    )

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.divider()

    # ======================================================
    # PIE CHART
    # ======================================================

    st.subheader("🥧 Portfolio Allocation")

    pie_df = display_df.copy()

    pie_df["Investment"] = pie_df["Quantity"] * pie_df["Buy Price"]

    fig = px.pie(pie_df, names="Symbol", values="Investment", hole=0.5)

    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ======================================================
    # EXPORT
    # ======================================================

    st.subheader("📥 Export Portfolio")

    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        display_df.to_excel(writer, index=False, sheet_name="Portfolio")

    st.download_button(
        "📄 Download Excel",
        data=output.getvalue(),
        file_name="portfolio.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.divider()

    # ======================================================
    # DELETE
    # ======================================================

    st.subheader("🗑 Delete Holding")

    stock_id = st.number_input("Portfolio ID", min_value=1, step=1, key="delete_id")

    if st.button("Delete Holding", key="delete_btn"):

        delete_stock(stock_id)

        st.success("Holding Deleted")

        st.rerun()
