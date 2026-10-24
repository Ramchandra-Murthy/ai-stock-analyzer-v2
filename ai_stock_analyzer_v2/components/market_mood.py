import streamlit as st


def show_market_mood(score):
    """
    Professional AI Market Mood Widget
    """

    if score >= 75:
        mood = "🟢 BULLISH"
        color = "#16a34a"

    elif score >= 50:
        mood = "🟡 NEUTRAL"
        color = "#eab308"

    else:
        mood = "🔴 BEARISH"
        color = "#dc2626"

    st.subheader("🤖 AI Market Mood")

    st.progress(score / 100)

    st.markdown(
        f"""
        <div style="
            background:#ffffff;
            padding:15px;
            border-radius:12px;
            border-left:8px solid {color};
            box-shadow:0 2px 8px rgba(0,0,0,0.08);
            margin-top:15px;
        ">
            <h2 style="margin:0;">{score}/100</h2>
            <h4 style="margin-top:8px;color:{color};">
                {mood}
            </h4>
        </div>
        """,
        unsafe_allow_html=True,
    )
