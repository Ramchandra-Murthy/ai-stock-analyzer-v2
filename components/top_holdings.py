import pandas as pd
import streamlit as st

from portfolio.portfolio import delete_stock


def show_top_holdings(df, top_n=5):
    """
    Display Top Holdings.
    """

    if df.empty:
        st.info("No holdings available.")
        return

    table = df.sort_values(by="Current Value", ascending=False).head(top_n).copy()

    # ----------------------------
    # Format numbers
    # ----------------------------

    display = table[
        [
            "symbol",
            "quantity",
            "buy_price",
            "CMP",
            "Current Value",
            "Profit",
            "Return %",
        ]
    ].copy()

    display.columns = [
        "Symbol",
        "Qty",
        "Buy Price",
        "CMP",
        "Current Value",
        "Profit",
        "Return %",
    ]

    def money(value):
        return "N/A" if pd.isna(value) else f"₹{value:,.2f}"

    def percent(value):
        return "N/A" if pd.isna(value) else f"{value:.2f}%"

    display["Buy Price"] = display["Buy Price"].map(money)
    display["CMP"] = display["CMP"].map(money)
    display["Current Value"] = display["Current Value"].map(money)
    display["Profit"] = display["Profit"].map(money)
    display["Return %"] = display["Return %"].map(percent)

    st.dataframe(display, use_container_width=True, hide_index=True)

    st.divider()

    # ----------------------------
    # Delete Holding
    # ----------------------------

    col1, col2 = st.columns([3, 1])

    with col1:

        selected = st.selectbox(
            "Delete Holding",
            table["id"],
            format_func=lambda x: table.loc[table["id"] == x, "symbol"].iloc[0],
        )

    with col2:

        st.write("")
        st.write("")

        if st.button("🗑 Delete", use_container_width=True):
            delete_stock(selected)
            st.success("Holding deleted.")
            st.rerun()
