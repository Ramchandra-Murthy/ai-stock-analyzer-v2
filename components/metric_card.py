import streamlit as st


def metric_card(title, value, delta=None):
    """
    Display a professional KPI card.
    """

    with st.container():

        st.markdown(
            f"""
            <div style="
                background:white;
                padding:18px;
                border-radius:12px;
                border:1px solid #e6e6e6;
                box-shadow:0 2px 8px rgba(0,0,0,0.08);
                margin-bottom:10px;
            ">

            <h5 style="margin:0;color:#777;">
                {title}
            </h5>

            <h2 style="margin:5px 0;">
                {value}
            </h2>

            <p style="color:green;font-weight:bold;">
                {delta if delta else ""}
            </p>

            </div>
            """,
            unsafe_allow_html=True,
        )
