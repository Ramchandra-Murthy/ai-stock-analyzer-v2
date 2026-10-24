from types import SimpleNamespace

import pytest

from services.watchlist_identity import (
    WatchlistAuthenticationError,
    get_authenticated_user_id,
)


def test_resolves_issuer_scoped_oidc_subject():
    user = {"is_logged_in": True, "iss": "https://identity.example", "sub": "user-123"}
    assert get_authenticated_user_id(user) == "oidc:https://identity.example:user-123"


def test_supports_attribute_based_user_object():
    user = SimpleNamespace(is_logged_in=True, iss="https://identity.example", sub="user-123")
    assert get_authenticated_user_id(user) == "oidc:https://identity.example:user-123"


def test_rejects_logged_out_user():
    with pytest.raises(WatchlistAuthenticationError, match="Sign in"):
        get_authenticated_user_id({"is_logged_in": False, "iss": "issuer", "sub": "user"})


@pytest.mark.parametrize(
    "claims",
    [
        {"is_logged_in": True, "sub": "user"},
        {"is_logged_in": True, "iss": "issuer"},
        {"is_logged_in": True, "iss": " ", "sub": "user"},
        {"is_logged_in": True, "iss": "issuer", "sub": " "},
    ],
)
def test_rejects_missing_or_blank_identity_claims(claims):
    with pytest.raises(WatchlistAuthenticationError):
        get_authenticated_user_id(claims)


def test_same_subject_from_different_issuers_is_distinct():
    first = {"is_logged_in": True, "iss": "issuer-a", "sub": "user-123"}
    second = {"is_logged_in": True, "iss": "issuer-b", "sub": "user-123"}
    assert get_authenticated_user_id(first) != get_authenticated_user_id(second)
