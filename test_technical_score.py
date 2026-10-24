import streamlit as st

from services.technical_score_service import calculate_technical_score
from services.technical_service import get_price_history

st.title("Technical Score Test")

symbol = st.text_input("Symbol", "RELIANCE")

df = get_price_history(symbol)

score, reasons = calculate_technical_score(df)

st.metric("Technical Score", score)

st.progress(score / 100)

st.subheader("Reasons")

if reasons:
    for reason in reasons:
        st.success(reason)
else:
    st.info("No significant technical signals detected.")
