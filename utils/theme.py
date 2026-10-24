import streamlit as st


def load_theme():

    st.markdown(
        """
        <style>

        .main {
            background-color: #F8FAFC;
        }

        div[data-testid="stMetric"]{
            background-color:white;
            border-radius:15px;
            padding:18px;
            border:1px solid #E5E7EB;
            box-shadow:0px 2px 6px rgba(0,0,0,.05);
        }

        h1{
            color:#0F172A;
            font-weight:700;
        }

        h2,h3{
            color:#1E293B;
        }

        .stButton>button{

            border-radius:12px;

            font-weight:bold;

            height:45px;

            width:100%;

        }

        </style>
        """,
        unsafe_allow_html=True,
    )
