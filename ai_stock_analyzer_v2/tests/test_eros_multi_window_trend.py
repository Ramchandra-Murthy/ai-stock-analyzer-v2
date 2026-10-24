import pandas as pd

from scanner.eros_multi_window_trend import analyze_eros_multi_window_trend


def _history(scores: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Timestamp": pd.date_range("2026-09-18 10:00", periods=len(scores), freq="5min"),
            "Symbol": ["AAA"] * len(scores),
            "Exchange": ["NSE"] * len(scores),
            "Fusion Score": scores,
        }
    )


def test_multi_window_trend_detects_aligned_rise():
    result = analyze_eros_multi_window_trend(_history([50, 55, 60, 70, 85, 95]))
    row = result.iloc[0]

    assert row["2-observation Change"] == 25.0
    assert row["3-observation Change"] == 35.0
    assert row["5-observation Change"] == 45.0
    assert row["Window Alignment"] == "RISING"


def test_multi_window_trend_detects_mixed_windows():
    result = analyze_eros_multi_window_trend(_history([50, 60, 70, 55, 65, 60]))

    assert result.iloc[0]["Window Alignment"] == "MIXED"


def test_multi_window_trend_handles_insufficient_history():
    result = analyze_eros_multi_window_trend(_history([50, 60]))

    assert result.iloc[0]["Window Alignment"] == "INSUFFICIENT DATA"
