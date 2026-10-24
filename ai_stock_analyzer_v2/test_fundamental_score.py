import streamlit as st

from services.fundamental_score_service import calculate_fundamental_score
from services.research_service import get_stock_profile

st.title("Fundamental Score Test")

symbol = st.text_input("Symbol", "RELIANCE")

profile = get_stock_profile(symbol)

st.json(profile)

score, reasons = calculate_fundamental_score(profile)

st.metric("Fundamental Score", score)

st.progress(score / 100)

st.subheader("Reasons")

if reasons:
    for reason in reasons:
        st.success(reason)
else:
    st.info("No significant fundamental signals detected.")

st.subheader("Profile")

st.json(profile)
