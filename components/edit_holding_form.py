import streamlit as st

from portfolio.portfolio import update_stock


def show_edit_holding_form(df):

    st.subheader("✏️ Edit Holding")

    if df.empty:
        st.info("No holdings available.")
        return

    selected_id = st.selectbox(
        "Select Holding",
        df["id"],
        format_func=lambda x: df.loc[df["id"] == x, "symbol"].iloc[0],
    )

    row = df[df["id"] == selected_id].iloc[0]

    quantity = st.number_input("Quantity", min_value=1, value=int(row["quantity"]), step=1)

    buy_price = st.number_input(
        "Buy Price (₹)",
        min_value=0.0,
        value=float(row["buy_price"]),
        step=0.05,
        format="%.2f",
    )

    if st.button("💾 Update Holding", use_container_width=True):

        update_stock(selected_id, int(quantity), float(buy_price))

        st.success("Holding updated successfully!")

        st.rerun()
