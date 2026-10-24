import pandas as pd

from scanner.eros_regime_quality import analyze_eros_regime_quality


def _history():
    return pd.DataFrame(
        {
            "Timestamp": pd.date_range("2026-09-20 09:15", periods=4, freq="5min"),
            "Regime": ["RISING DOMINANT"] * 4,
            "Rising Breadth %": [70, 72, 68, 75],
            "Falling Breadth %": [30, 28, 32, 25],
            "Average Trend Confidence %": [65, 67, 64, 70],
        }
    )


def test_reports_latest_regime_quality_dimensions():
    result = analyze_eros_regime_quality(_history())
    row = result.iloc[0]

    assert row["Current Regime"] == "RISING DOMINANT"
    assert row["Regime Streak"] == 4
    assert row["Current Regime Snapshots"] == 4
    assert row["Latest Breadth Strength"] == 50.0
    assert row["Latest Average Trend Confidence %"] == 70.0
    assert row["Regime Breadth Range"] == 7.0
    assert row["Regime Confidence Range"] == 6.0


def test_invalid_input_returns_empty():
    assert analyze_eros_regime_quality(None).empty
    assert analyze_eros_regime_quality(pd.DataFrame()).empty
