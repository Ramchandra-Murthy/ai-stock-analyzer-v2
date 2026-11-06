"""Finite numeric input validation for the shared watchlist service."""

import pytest

from services import watchlist_service as watchlists


@pytest.mark.parametrize(
    "details",
    [
        {"entry_price": float("nan")},
        {"stop_loss": float("inf")},
        {"target_price": float("-inf")},
        {"quantity": float("inf")},
        {"quantity": 2.5},
    ],
)
def test_watchlist_rejects_non_finite_prices_and_fractional_quantity(
    tmp_path, monkeypatch, details
):
    monkeypatch.setenv("WATCHLIST_DATABASE_PATH", str(tmp_path / "watchlists.sqlite3"))
    watchlist_id = watchlists.create_watchlist("owner", "My Watchlist")
    with pytest.raises(watchlists.WatchlistError):
        watchlists.add_symbol("owner", watchlist_id, "INVALID", details)
