import pandas as pd

from algorithmic_trading.algorithmic_scanner import _result_frame


def test_result_frame_sorts_by_signal_score() -> None:
    rows = [
        {
            "symbol": "AAA",
            "exchange": "NSE",
            "ticker": "AAA.NS",
            "price": 100.0,
            "regime": "BULLISH",
            "regime_score": 3,
            "relative_return_pct": 4.0,
            "signal": "LONG",
            "signal_score": 34.0,
            "quantity": 10,
            "risk_budget": 1000.0,
        },
        {
            "symbol": "BBB",
            "exchange": "NSE",
            "ticker": "BBB.NS",
            "price": 100.0,
            "regime": "INCONCLUSIVE",
            "regime_score": 0,
            "relative_return_pct": 1.0,
            "signal": "FLAT",
            "signal_score": 1.0,
            "quantity": 10,
            "risk_budget": 1000.0,
        },
    ]
    result = _result_frame(rows)
    assert isinstance(result, pd.DataFrame)
    assert result.iloc[0]["symbol"] == "AAA"
