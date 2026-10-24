"""Regression tests: the portfolio dashboard must survive a total live-price outage.

When no holding had a live price (provider outage, rate limiting, blocked market data)
the profit/return columns held only ``None``. That dtype made ``idxmax()`` raise
``ValueError`` and number formatting raise ``TypeError``, so the default landing page
crashed. Mixed price availability already worked because pandas turns ``None`` into NaN.
"""

import importlib
import sys
from unittest.mock import MagicMock

import pandas as pd
import pytest

from services import portfolio_service


def _holdings() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": [1, 2],
            "symbol": ["AAA.NS", "BBB.NS"],
            "quantity": [10, 5],
            "buy_price": [100.0, 200.0],
        }
    )


def _quote(price):
    return {
        "price": price,
        "observed_at": None if price is None else "2026-10-16",
        "source": "stub",
        "frequency": "daily",
        "change_pct": None,
    }


def _valued(monkeypatch, prices: dict) -> pd.DataFrame:
    monkeypatch.setattr(portfolio_service, "load_portfolio", _holdings)
    monkeypatch.setattr(
        portfolio_service, "get_latest_available_price", lambda symbol: _quote(prices[symbol])
    )
    return portfolio_service.get_portfolio()


@pytest.fixture
def streamlit_stub(monkeypatch):
    """A recording stand-in for streamlit so component modules import and run anywhere."""
    stub = MagicMock(name="streamlit")
    stub.button.return_value = False
    stub.columns.side_effect = lambda spec: [
        MagicMock() for _ in range(spec if isinstance(spec, int) else len(spec))
    ]
    monkeypatch.setitem(sys.modules, "streamlit", stub)
    for name in ("components.portfolio_analytics", "components.top_holdings"):
        monkeypatch.delitem(sys.modules, name, raising=False)
    yield stub
    for name in ("components.portfolio_analytics", "components.top_holdings"):
        sys.modules.pop(name, None)


def test_all_prices_missing_gives_numeric_nan_columns(monkeypatch) -> None:
    df = _valued(monkeypatch, {"AAA.NS": None, "BBB.NS": None})

    for column in ("CMP", "Current Value", "Profit", "Return %"):
        assert pd.api.types.is_float_dtype(df[column]), column
        assert df[column].isna().all()


def test_partial_prices_still_compute_values(monkeypatch) -> None:
    df = _valued(monkeypatch, {"AAA.NS": 110.0, "BBB.NS": None})

    assert df.loc[0, "Profit"] == 100.0
    assert df.loc[0, "Return %"] == 10.0
    assert pd.isna(df.loc[1, "Profit"])


def test_summary_with_no_prices_does_not_raise(monkeypatch) -> None:
    summary = portfolio_service.get_summary(_valued(monkeypatch, {"AAA.NS": None, "BBB.NS": None}))

    assert summary["holdings"] == 2
    assert summary["current_value"] == 0


def test_analytics_shows_notice_when_no_prices(monkeypatch, streamlit_stub) -> None:
    df = _valued(monkeypatch, {"AAA.NS": None, "BBB.NS": None})
    module = importlib.import_module("components.portfolio_analytics")

    module.show_portfolio_analytics(df)  # used to raise ValueError("Encountered all NA values")

    streamlit_stub.info.assert_called_once()
    streamlit_stub.metric.assert_not_called()


def test_analytics_ignores_unpriced_holdings(monkeypatch, streamlit_stub) -> None:
    df = _valued(monkeypatch, {"AAA.NS": 110.0, "BBB.NS": None})
    module = importlib.import_module("components.portfolio_analytics")

    module.show_portfolio_analytics(df)

    first_metric_args = streamlit_stub.metric.call_args_list[0].args
    assert first_metric_args[1] == "AAA.NS"


def test_top_holdings_renders_na_instead_of_crashing(monkeypatch, streamlit_stub) -> None:
    df = _valued(monkeypatch, {"AAA.NS": None, "BBB.NS": None})
    module = importlib.import_module("components.top_holdings")

    module.show_top_holdings(df)

    shown = streamlit_stub.dataframe.call_args.args[0]
    assert set(shown["CMP"]) == {"N/A"}
    assert set(shown["Profit"]) == {"N/A"}
    assert set(shown["Return %"]) == {"N/A"}
