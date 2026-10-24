from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class WatchlistAuthenticationError(PermissionError):
    """Raised when no trusted authenticated identity is available."""


def _claim(user: Any, name: str) -> Any:
    """Read a claim from a mapping-like or attribute-based user object."""
    if isinstance(user, Mapping):
        return user.get(name)
    getter = getattr(user, "get", None)
    if callable(getter):
        value = getter(name)
        if value is not None:
            return value
    return getattr(user, name, None)


def get_authenticated_user_id(user: Any) -> str:
    """Return an issuer-scoped OIDC subject or reject unauthenticated users.

    Pass Streamlit's authenticated st.user object directly. Never accept IDs
    from form fields, query parameters, or other user-controlled input.
    """
    if _claim(user, "is_logged_in") is not True:
        raise WatchlistAuthenticationError("Sign in before accessing personal watchlists.")

    issuer = _claim(user, "iss")
    subject = _claim(user, "sub")
    if not isinstance(issuer, str) or not issuer.strip():
        raise WatchlistAuthenticationError("Authenticated identity is missing its OIDC issuer.")
    if not isinstance(subject, str) or not subject.strip():
        raise WatchlistAuthenticationError("Authenticated identity is missing its OIDC subject.")

    return f"oidc:{issuer.strip()}:{subject.strip()}"
