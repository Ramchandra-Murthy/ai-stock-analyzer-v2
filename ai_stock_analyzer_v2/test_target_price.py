import streamlit as st

from services.target_price_service import calculate_target_price
from services.technical_score_service import calculate_technical_score
from services.technical_service import get_price_history

st.title("🎯 Target Price Engine Test")

symbol = (
    st.text_input(
        "NSE Symbol",
        value="RELIANCE",
    )
    .strip()
    .upper()
)

if st.button("Calculate"):

    history = get_price_history(symbol)

    if history is None or history.empty:

        st.error("Historical data unavailable.")

    else:

        technical_score, reasons = calculate_technical_score(history)

        result = calculate_target_price(
            history,
            technical_score,
        )

        st.metric(
            "Technical Score",
            f"{technical_score}/100",
        )

        st.write("### Trade Planning")

        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric(
                "Current Price",
                f"₹{result['current_price']:,.2f}",
            )

        with c2:
            st.metric(
                "Target Price",
                f"₹{result['target_price']:,.2f}",
            )

        with c3:
            st.metric(
                "Stop Loss",
                f"₹{result['stop_loss']:,.2f}",
            )

        c4, c5, c6 = st.columns(3)

        with c4:
            st.metric(
                "Potential Upside",
                f"{result['upside_percent']:.2f}%",
            )

        with c5:
            st.metric(
                "Risk / Reward",
                f"1 : {result['risk_reward']:.2f}",
            )

        with c6:
            st.metric(
                "ATR",
                f"₹{result['atr']:,.2f}",
            )

        st.write("### Technical Reasons")

        for reason in reasons:
            st.write(f"✅ {reason}")
