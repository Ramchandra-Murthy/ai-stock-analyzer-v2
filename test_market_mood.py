import streamlit as st

from components.market_mood import show_market_mood

st.title("Market Mood Test")

show_market_mood(82)
