"""Integration tests for the AI Trading Command Center page."""

# Ruff cannot reliably classify the Streamlit testing import with this module alias.
# Keep the import explicit and scope the isort suppression to this test file.
# ruff: noqa: I001

from __future__ import annotations

import pathlib

import pandas as pd
import streamlit.testing.v1 as streamlit_testing
import yfinance as yf

import ai_trading.ml_scanner as ml_scanner
import modules.intraday as intraday

PAGE = pathlib.Path(__file__).resolve().parents[1] / "pages" / "AI_Trading_Command_Center.py"


def _live_board() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Rank": 1,
                "Symbol": "RELIANCE",
                "Exchange": "NSE",
                "Price": 2_000.0,
                "1-min change %": 0.4,
                "5-min change %": 0.8,
                "Today change %": 1.2,
                "Volume surge x": 1.5,
                "Breakout": True,
                "Relative Strength": 82.0,
                "Last update": "2026-10-03 10:00:00 IST",
            }
        ]
    )


def _ml_result() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "symbol": "RELIANCE",
                "exchange": "NSE",
                "latest_price": 2_000.0,
                "signal": "LONG",
                "confidence_pct": 80.0,
                "probability_up_pct": 75.0,
                "validation_pct": 70.0,
                "trend_pct": 3.0,
                "regime": "BULL",
                "decision_reason": "validated trend",
            }
        ]
    )


def test_command_center_renders_when_market_is_closed(monkeypatch) -> None:
    monkeypatch.setattr(intraday, "_market_session_is_open", lambda now: False)

    app = streamlit_testing.AppTest.from_file(PAGE).run()

    assert app.button[0].disabled
    assert any("Market is closed" in message.value for message in app.info)


def test_command_center_cycle_updates_paper_portfolio(monkeypatch) -> None:
    monkeypatch.setattr(intraday, "_market_session_is_open", lambda now: True)
    monkeypatch.setattr(
        intraday,
        "_fetch_live_board",
        lambda: (_live_board(), [], {}, {"scan_seconds": 0.1, "usable": 1}),
    )
    monkeypatch.setattr(ml_scanner, "scan_universe", lambda *args, **kwargs: _ml_result())

    prices = pd.DataFrame(
        {("Close", "RELIANCE.NS"): [1_950.0, 2_000.0]},
        index=pd.date_range("2026-10-02", periods=2, freq="D"),
    )
    prices.columns = pd.MultiIndex.from_tuples(prices.columns)

    monkeypatch.setattr(yf, "download", lambda *args, **kwargs: prices)

    app = streamlit_testing.AppTest.from_file(PAGE).run()
    app.button[0].click().run()

    assert any(
        "Cycle complete: 1 simulated paper fills." in message.value for message in app.success
    )
    assert any("Current paper portfolio is within" in message.value for message in app.success)
    assert app.session_state["ai_paper_portfolio"].positions == {"RELIANCE": 10}
    assert app.session_state["ai_paper_prices"] == {"RELIANCE": 2_000.0}
