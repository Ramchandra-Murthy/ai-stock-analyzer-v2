import streamlit as st

from services.recommendation_service import generate_recommendation
from services.score_service import calculate_investment_score

st.title("AI Recommendation Test")

# Reconstructed V2 pipeline:
# component scores -> authoritative Investment Score -> recommendation.
investment_score, breakdown = calculate_investment_score(
    technical_score=88,
    fundamental_score=91,
    ai_result={"score": 78},
    data={
        # Stability inputs are optional; unavailable inputs are handled
        # by the score service without forcing a zero score.
    },
)

result = generate_recommendation(investment_score)

st.metric("Investment Score", investment_score)
st.metric("Confidence", f"{result['confidence']}%")

st.success(result["recommendation"])

st.write("Investment Score Breakdown")
st.json(breakdown)

st.write("Recommendation Result")
st.json(result)
