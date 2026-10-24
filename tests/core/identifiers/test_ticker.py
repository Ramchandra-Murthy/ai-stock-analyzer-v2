from __future__ import annotations

import pytest

from core.identifiers.ticker import Ticker
from core.types.enums import MarketExchange


def test_ticker_creation() -> None:
    t = Ticker("rel", MarketExchange.NSE)
    assert t.symbol == "REL"
    assert t.exchange == MarketExchange.NSE
    assert t.to_dict()["symbol"] == "REL"


def test_ticker_invalid() -> None:
    with pytest.raises(ValueError):
        Ticker("", MarketExchange.NSE)
