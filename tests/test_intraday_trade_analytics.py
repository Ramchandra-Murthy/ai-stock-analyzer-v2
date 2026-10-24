"""Tests for trade-journal performance analytics."""

from services.intraday_trade_analytics import performance_summary, setup_performance


def _history():
    return [
        {"Setup": "BREAKOUT", "Side": "LONG", "Risk": 100, "PnL": 200},
        {"Setup": "BREAKOUT", "Side": "LONG", "Risk": 100, "PnL": -50},
        {"Setup": "PULLBACK", "Side": "SHORT", "Risk": 200, "PnL": None},
    ]


def test_performance_summary_uses_closed_trades():
    summary = performance_summary(_history()).iloc[0]
    assert summary["Trades"] == 3
    assert summary["Closed"] == 2
    assert summary["Wins"] == 1
    assert summary["Win rate %"] == 50
    assert summary["Net PnL"] == 150
    assert summary["Average R"] == 0.75


def test_setup_performance_groups_closed_results():
    result = setup_performance(_history())
    breakout = result[result["Setup"] == "BREAKOUT"].iloc[0]
    assert breakout["Closed"] == 2
    assert breakout["Net PnL"] == 150
