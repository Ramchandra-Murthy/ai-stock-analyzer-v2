import pandas as pd

from modules.market_movers import _extract_frame, _ticker, _top_table, _window_change


def test_ticker_normalization_preserves_exchange_suffix():
    assert _ticker("RELIANCE", "NSE") == "RELIANCE.NS"
    assert _ticker("500325", "BSE") == "500325.BO"
    assert _ticker("TCS.NS", "BSE") == "TCS.NS"


def test_window_change_uses_requested_bar_baseline():
    close = pd.Series([100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0])
    assert _window_change(close, 1) == 0.952
    assert _window_change(close, 3) == 2.913
    assert _window_change(close, 8) is None


def test_top_table_separates_gainers_and_losers():
    frame = pd.DataFrame(
        {
            "Symbol": ["A", "B", "C"],
            "Change 5m %": [1.2, -0.8, 0.0],
        }
    )
    assert _top_table(frame, "Change 5m %", True, 10)["Symbol"].tolist() == ["A"]
    assert _top_table(frame, "Change 5m %", False, 10)["Symbol"].tolist() == ["B"]


def test_extract_frame_handles_plain_ohlcv_data():
    frame = pd.DataFrame(
        {
            "Open": [10.0, 11.0],
            "High": [12.0, 12.0],
            "Low": [9.0, 10.0],
            "Close": [11.0, 11.5],
            "Volume": [100, 120],
        }
    )
    result = _extract_frame(frame, "TEST.NS")
    assert set(result.columns) == {"Open", "High", "Low", "Close", "Volume"}
    assert result["Close"].tolist() == [11.0, 11.5]
