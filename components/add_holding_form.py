import streamlit as st

from portfolio.portfolio import add_stock


def show_add_holding_form():

    st.subheader("➕ Add New Holding")

    with st.form("add_holding_form"):

        symbol = st.text_input("Stock Symbol", placeholder="RELIANCE.NS")

        quantity = st.number_input("Quantity", min_value=1, step=1)

        buy_price = st.number_input("Buy Price (₹)", min_value=0.0, step=0.05, format="%.2f")

        submitted = st.form_submit_button("💾 Save Holding", use_container_width=True)

        if submitted:

            if symbol.strip() == "":
                st.error("Please enter a stock symbol.")

            else:
                add_stock(symbol.upper(), int(quantity), float(buy_price))

                st.success(f"{symbol.upper()} added successfully!")

                st.rerun()
