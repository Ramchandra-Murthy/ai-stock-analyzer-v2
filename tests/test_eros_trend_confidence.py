import pandas as pd

from scanner.eros_trend_confidence import analyze_eros_trend_confidence


def _history(values: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Timestamp": pd.date_range(
                "2026-09-19 09:15",
                periods=len(values),
                freq="min",
            ),
            "Symbol": ["ABC"] * len(values),
            "Exchange": ["NSE"] * len(values),
            "Fusion Score": values,
        }
    )


def test_detects_high_confidence_rising_trend():
    result = analyze_eros_trend_confidence(_history([40, 42, 44, 46, 48]))
    row = result.iloc[0]
    assert row["Trend Consensus"] == "RISING CONFIRMED"
    assert row["Direction"] == "RISING"
    assert row["Persistence"] == "PERSISTENT"
    assert row["Trend Quality"] == "COHERENT"
    assert row["Trend Confidence %"] == 100.0
    assert row["Confidence"] == "HIGH"


def test_detects_low_confidence_mixed_trend():
    result = analyze_eros_trend_confidence(_history([40, 42, 41, 43, 42]))
    row = result.iloc[0]
    assert row["Trend Consensus"] == "MIXED"
    assert row["Trend Quality"] == "MIXED"
    assert row["Confidence"] == "LOW"


def test_handles_insufficient_data():
    result = analyze_eros_trend_confidence(_history([40]))
    row = result.iloc[0]
    assert row["Confidence"] == "INSUFFICIENT DATA"
    assert row["Trend Confidence %"] == 0.0
