"""User-facing sign-in helper for authenticated watchlist pages."""

import streamlit as st


def render_watchlist_sign_in(message: str, *, key: str) -> None:
    """Explain the authentication requirement and offer Streamlit's OIDC login."""
    st.warning(message)
    if st.button("Sign in", key=key, type="primary"):
        try:
            st.login()
        except Exception:
            st.error(
                "Sign-in is not configured for this deployment. Configure the "
                "[auth] settings in Streamlit secrets and register this app's "
                "OAuth redirect URL with your identity provider."
            )
            st.caption(
                "See docs/watchlist-authentication.md for deployment instructions. "
                "Never commit client secrets or cookie secrets to Git."
            )
