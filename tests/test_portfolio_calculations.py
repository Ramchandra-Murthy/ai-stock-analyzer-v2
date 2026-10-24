"""Tests for watchlist portfolio calculations."""

import pytest

from services.portfolio_calculations import is_actual_holding, position_valuation


def test_watching_record_is_not_counted_as_a_holding():
    record = {"status": "Watching", "entry_price": 100, "quantity": 1}
    assert not is_actual_holding(record)
    valuation = position_valuation(record, 110)
    assert valuation["invested"] is None
    assert valuation["current_value"] is None
    assert valuation["pnl"] is None


def test_bought_position_calculates_invested_value_and_pnl():
    record = {"status": "Bought", "entry_price": 100, "quantity": 10}
    valuation = position_valuation(record, 110)
    assert valuation["is_holding"] is True
    assert valuation["invested"] == 1000
    assert valuation["current_value"] == 1100
    assert valuation["pnl"] == 100
    assert valuation["pnl_pct"] == pytest.approx(10)


def test_incomplete_bought_record_is_not_counted_as_a_holding():
    for record in (
        {"status": "Bought", "entry_price": None, "quantity": 1},
        {"status": "Bought", "entry_price": 100, "quantity": None},
        {"status": "Bought", "entry_price": 0, "quantity": 1},
    ):
        assert not is_actual_holding(record)
        assert position_valuation(record, 110)["invested"] is None


def test_futures_and_options_use_lot_size_for_bought_positions():
    record = {
        "status": "Bought",
        "entry_price": 100,
        "quantity": 2,
        "asset_details": {"instrument_type": "Options", "lot_size": 25},
    }
    valuation = position_valuation(record, 110)
    assert valuation["effective_quantity"] == 50
    assert valuation["invested"] == 5000
    assert valuation["current_value"] == 5500
    assert valuation["pnl"] == 500


def test_bought_position_without_quote_keeps_invested_cost_only():
    record = {"status": "Bought", "entry_price": 100, "quantity": 2}
    valuation = position_valuation(record, None)
    assert valuation["invested"] == 200
    assert valuation["current_value"] is None
    assert valuation["pnl"] is None
