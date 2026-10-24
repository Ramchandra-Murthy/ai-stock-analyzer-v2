from unittest.mock import patch

import pandas as pd

from scanner.market_scanner import _analyze_history


def test_market_scanner_preserves_signal_confidence() -> None:
    history = pd.DataFrame(
        {
            "Open": [100.0] * 50,
            "High": [101.0] * 50,
            "Low": [99.0] * 50,
            "Close": [100.0] * 50,
            "Volume": [1_000_000] * 50,
            "RSI_14": [50.0] * 50,
            "MACD": [1.0] * 50,
            "ATR": [2.0] * 50,
        }
    )
    signal = {
        "Status": "OK",
        "Score": 45,
        "Confidence": 55.0,
        "Risk": "Medium",
        "Recommendation": "HOLD",
    }

    with (
        patch("scanner.market_scanner._extract_history_frame", return_value=history),
        patch("scanner.market_scanner.calculate_sma", side_effect=lambda df, *_: df),
        patch("scanner.market_scanner.calculate_ema", side_effect=lambda df, *_: df),
        patch("scanner.market_scanner.calculate_rsi", side_effect=lambda df, *_: df),
        patch("scanner.market_scanner.calculate_macd", side_effect=lambda df, *_: df),
        patch("scanner.market_scanner.calculate_histogram", side_effect=lambda df, *_: df),
        patch("scanner.market_scanner.calculate_bollinger", side_effect=lambda df, *_: df),
        patch("scanner.market_scanner.calculate_atr", side_effect=lambda df, *_: df),
        patch(
            "scanner.market_scanner.calculate_support_resistance",
            side_effect=lambda df, *_: df,
        ),
        patch("scanner.market_scanner.detect_trend", return_value={"Trend": "Bullish"}),
        patch("scanner.market_scanner.generate_signal", return_value=signal),
        patch("scanner.market_scanner.detect_breakout"),
    ):
        row = _analyze_history("CHENNPETRO.NS", history, 10_000_000.0)

    assert row is not None
    assert row["AI Score"] == 45
    assert row["Confidence"] == 55.0
