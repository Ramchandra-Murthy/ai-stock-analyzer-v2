import streamlit as st

from services.live_market_service import get_market_indices

st.title("Live Market Dashboard")

data = get_market_indices()

cols = st.columns(4)

for col, (name, value) in zip(cols, data.items(), strict=False):

    with col:

        if value:

            st.metric(name, f"{value['price']:.2f}", f"{value['percent']:.2f}%")
