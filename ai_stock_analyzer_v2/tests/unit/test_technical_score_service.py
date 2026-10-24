import pandas as pd

from services.technical_score_service import calculate_technical_score


def test_technical_score_empty_history():
    score, reasons = calculate_technical_score(pd.DataFrame())
    assert score is None
    assert reasons == ["Historical price data is unavailable"]


def test_technical_score_is_bounded_and_uses_indicators():
    frame = pd.DataFrame(
        [
            {
                "RSI": 55,
                "EMA20": 110,
                "EMA50": 100,
                "EMA200": 90,
                "MACD": 2,
                "MACD_Signal": 1,
                "Close": 115,
                "Resistance": 112,
                "Support": 100,
            }
        ]
    )

    score, reasons = calculate_technical_score(frame)

    assert 0 <= score <= 100
    assert score > 50
    assert any("bullish" in reason.lower() for reason in reasons)
