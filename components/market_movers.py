import streamlit as st

from services.market_service import get_top_movers


def show_market_movers():
    """
    Displays top gainers and losers.
    """

    gainers, losers = get_top_movers()

    st.subheader("🔥 Market Movers")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🟢 Top Gainers")

        if gainers.empty:
            st.info("No data available.")
        else:
            st.dataframe(
                gainers,
                use_container_width=True,
                hide_index=True,
            )

    with col2:
        st.markdown("### 🔴 Top Losers")

        if losers.empty:
            st.info("No data available.")
        else:
            st.dataframe(
                losers,
                use_container_width=True,
                hide_index=True,
            )
