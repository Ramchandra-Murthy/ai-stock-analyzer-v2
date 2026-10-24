"""Tests for the no-login single-owner watchlist adapter."""

from services.watchlist_ui import get_or_create_default_watchlist


def test_adapter_creates_seeded_default_list_without_login(tmp_path, monkeypatch):
    monkeypatch.setenv("WATCHLIST_DATABASE_PATH", str(tmp_path / "watchlists.sqlite3"))
    owner_id, watchlist_id, symbols = get_or_create_default_watchlist(
        None, ["RELIANCE.NS", "TCS.NS"]
    )
    assert owner_id == "local-owner"
    assert symbols == ["RELIANCE.NS", "TCS.NS"]
    assert watchlist_id > 0


def test_adapter_shares_same_list_across_sessions(tmp_path, monkeypatch):
    monkeypatch.setenv("WATCHLIST_DATABASE_PATH", str(tmp_path / "watchlists.sqlite3"))
    _, first_id, _ = get_or_create_default_watchlist(None, ["RELIANCE.NS"])
    _, second_id, second_symbols = get_or_create_default_watchlist(None, ["TCS.NS"])
    assert first_id == second_id
    assert second_symbols == ["RELIANCE.NS"]
