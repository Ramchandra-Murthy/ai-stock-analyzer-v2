import streamlit as st

from components.metric_card import metric_card

st.title("Metric Card Test")

col1, col2, col3 = st.columns(3)

with col1:
    metric_card("Current Price", "₹1,278", "+2.3%")

with col2:
    metric_card("AI Score", "87/100", "BUY")

with col3:
    metric_card("Market Cap", "₹18.4 L Cr", "")
