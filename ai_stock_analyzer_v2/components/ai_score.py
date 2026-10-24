import streamlit as st


def show_ai_score(score=80):
    """
    Display AI Portfolio Health Score.
    """

    score = max(0, min(100, score))

    if score >= 90:
        color = "🟢"
        status = "Excellent"
        advice = "Your portfolio is well diversified. Continue monitoring."

    elif score >= 75:
        color = "🔵"
        status = "Good"
        advice = "Your portfolio is healthy. Minor improvements are possible."

    elif score >= 60:
        color = "🟡"
        status = "Average"
        advice = "Consider improving diversification and reducing risk."

    else:
        color = "🔴"
        status = "Needs Improvement"
        advice = "High portfolio risk detected. Review your holdings."

    # Progress Bar
    st.progress(score / 100)

    # Score Cards
    col1, col2 = st.columns(2)

    with col1:
        st.metric("AI Score", f"{score}/100")

    with col2:
        st.metric("Portfolio Status", status)

    # Recommendation
    st.info(f"{color} {advice}")
