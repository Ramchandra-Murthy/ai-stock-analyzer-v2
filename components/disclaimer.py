"""One shared research disclaimer for every Streamlit page.

The wording lives here so a legal or compliance edit is made once. The constant is plain text
so tests can read it without importing Streamlit.
"""

from __future__ import annotations

DISCLAIMER_TEXT = (
    "Research and education only. Nothing here is investment advice or a recommendation to "
    "buy or sell any security. Figures come from models and third-party data that can be "
    "delayed, incomplete or wrong, and past results do not predict future returns."
)


def show_disclaimer() -> None:
    """Render the disclaimer as a quiet caption under the page title."""
    import streamlit as st

    st.caption(f"⚠️ {DISCLAIMER_TEXT}")
