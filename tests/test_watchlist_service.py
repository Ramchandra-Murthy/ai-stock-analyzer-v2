"""Tests for persistent single-owner watchlist and saved investment details."""

import pytest

from services import watchlist_service as watchlists


@pytest.fixture
def database_path(tmp_path, monkeypatch):
    path = tmp_path / "watchlists.sqlite3"
    monkeypatch.setenv("WATCHLIST_DATABASE_PATH", str(path))
    return path


def test_symbols_and_details_persist(database_path):
    watchlist_id = watchlists.create_watchlist("anything", "My Watchlist")
    details = {
        "entry_price": 1250.5,
        "stop_loss": 1200,
        "target_price": 1400,
        "quantity": 10,
        "investment_type": "Swing",
        "purchase_date": "2026-10-11",
        "notes": "Breakout setup",
        "status": "Watching",
    }
    assert watchlists.add_symbol("anything", watchlist_id, "reliance.ns", details)
    assert watchlists.list_symbols("any-session", watchlist_id) == ["RELIANCE.NS"]
    record = watchlists.list_stock_records("any-session", watchlist_id)[0]
    assert record["entry_price"] == 1250.5
    assert record["stop_loss"] == 1200
    assert record["target_price"] == 1400
    assert record["quantity"] == 10
    assert record["investment_type"] == "Swing"
    assert record["purchase_date"] == "2026-10-11"
    assert record["notes"] == "Breakout setup"
    assert record["status"] == "Watching"


def test_all_sessions_share_one_watchlist(database_path):
    first_id = watchlists.create_watchlist("session-a", "My Watchlist")
    watchlists.add_symbol("session-a", first_id, "TCS")
    assert watchlists.list_symbols("session-b", first_id) == ["TCS"]
    assert watchlists.list_watchlists("session-b")[0]["name"] == "My Watchlist"


def test_update_details_and_remove_symbol(database_path):
    watchlist_id = watchlists.create_watchlist("owner", "My Watchlist")
    watchlists.add_symbol("owner", watchlist_id, "INFY")
    watchlists.update_stock_details(
        "owner",
        watchlist_id,
        "INFY",
        {
            "entry_price": 1800,
            "stop_loss": 1750,
            "target_price": 1950,
            "quantity": 5,
            "investment_type": "Delivery",
            "purchase_date": "2026-10-01",
            "notes": "Long-term idea",
            "status": "Bought",
        },
    )
    record = watchlists.list_stock_records("owner", watchlist_id)[0]
    assert record["entry_price"] == 1800
    assert record["status"] == "Bought"
    assert record["notes"] == "Long-term idea"
    assert watchlists.remove_symbol("owner", watchlist_id, "INFY")
    assert watchlists.list_stock_records("owner", watchlist_id) == []


def test_duplicate_symbols_and_invalid_values_are_rejected(database_path):
    watchlist_id = watchlists.create_watchlist("owner", "My Watchlist")
    assert watchlists.add_symbol("owner", watchlist_id, "TCS")
    assert not watchlists.add_symbol("other", watchlist_id, "tcs")
    with pytest.raises(watchlists.WatchlistError, match="valid stock symbol"):
        watchlists.add_symbol("owner", watchlist_id, "BAD SYMBOL")
    with pytest.raises(watchlists.WatchlistError, match="negative"):
        watchlists.add_symbol("owner", watchlist_id, "INFY", {"stop_loss": -1})
    with pytest.raises(watchlists.WatchlistError, match="Quantity"):
        watchlists.add_symbol("owner", watchlist_id, "INFY", {"quantity": 0})


def test_watchlist_operations_reject_blank_owner(database_path):
    with pytest.raises(watchlists.WatchlistError, match="owner"):
        watchlists.create_watchlist("", "My Watchlist")


def test_multi_asset_category_and_details_persist(database_path):
    watchlist_id = watchlists.create_watchlist("owner", "My Watchlist")
    details = {
        "entry_price": 125.0,
        "target_price": 150.0,
        "stop_loss": 110.0,
        "quantity": 8,
        "investment_type": "Investment",
        "purchase_date": "2026-10-11",
        "notes": "Manual NAV tracking",
        "status": "Bought",
        "asset_category": "Mutual Funds",
        "asset_details": {
            "instrument_name": "Example Flexi Cap Fund",
            "current_price_manual": 130.0,
            "units_quantity": 8.25,
            "scheme_details": "Direct Growth",
        },
    }
    assert watchlists.add_symbol("owner", watchlist_id, "MF-EXAMPLE-FLEXI-CAP", details)
    record = watchlists.list_stock_records("owner", watchlist_id)[0]
    assert record["asset_category"] == "Mutual Funds"
    assert record["asset_details"]["instrument_name"] == "Example Flexi Cap Fund"
    assert record["asset_details"]["current_price_manual"] == 130.0
    assert record["asset_details"]["units_quantity"] == 8.25

    details["asset_details"]["current_price_manual"] = 132.5
    watchlists.update_stock_details("owner", watchlist_id, "MF-EXAMPLE-FLEXI-CAP", details)
    updated = watchlists.list_stock_records("owner", watchlist_id)[0]
    assert updated["asset_details"]["current_price_manual"] == 132.5
