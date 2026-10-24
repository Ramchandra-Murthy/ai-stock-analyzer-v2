import pandas as pd

from scanner.eros_trend_quality import analyze_eros_trend_quality


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


def test_detects_coherent_rising_trend():
    result = analyze_eros_trend_quality(_history([40, 42, 44, 46, 48]))
    row = result.iloc[0]
    assert row["Direction"] == "RISING"
    assert row["Net Change"] == 8.0
    assert row["Directional Consistency %"] == 100.0
    assert row["Trend Efficiency %"] == 100.0
    assert row["Trend Quality"] == "COHERENT"


def test_detects_mixed_trend():
    result = analyze_eros_trend_quality(_history([40, 42, 41, 43, 42]))
    row = result.iloc[0]
    assert row["Direction"] == "FALLING"
    assert row["Directional Consistency %"] == 50.0
    assert row["Trend Efficiency %"] < 70.0
    assert row["Trend Quality"] == "MIXED"


def test_detects_stable_trend():
    result = analyze_eros_trend_quality(_history([40, 42, 42, 42]))
    assert result.loc[0, "Direction"] == "STABLE"
    assert result.loc[0, "Trend Quality"] == "STABLE"


def test_handles_new_signal():
    result = analyze_eros_trend_quality(_history([40]))
    assert result.loc[0, "Direction"] == "NEW"
    assert result.loc[0, "Trend Quality"] == "INSUFFICIENT DATA"
