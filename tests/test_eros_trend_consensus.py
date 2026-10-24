import pandas as pd

from scanner.eros_trend_consensus import analyze_eros_trend_consensus


def _history(values: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Timestamp": pd.date_range("2026-09-19 09:15", periods=len(values), freq="min"),
            "Symbol": ["ABC"] * len(values),
            "Exchange": ["NSE"] * len(values),
            "Fusion Score": values,
        }
    )


def test_rising_windows_are_confirmed():
    result = analyze_eros_trend_consensus(_history([40, 41, 43, 46, 50]))
    assert result.loc[0, "Window Alignment"] == "RISING"
    assert result.loc[0, "Trend Consensus"] == "RISING CONFIRMED"
    assert result.loc[0, "Lifecycle"] in {"PERSISTENT", "ACCELERATING"}


def test_falling_windows_are_confirmed():
    result = analyze_eros_trend_consensus(_history([50, 49, 47, 44, 40]))
    assert result.loc[0, "Window Alignment"] == "FALLING"
    assert result.loc[0, "Trend Consensus"] == "FALLING CONFIRMED"


def test_insufficient_history_is_explicit():
    result = analyze_eros_trend_consensus(_history([50, 51]))
    assert result.loc[0, "Trend Consensus"] == "INSUFFICIENT DATA"


def test_mixed_windows_are_not_confirmed():
    result = analyze_eros_trend_consensus(_history([40, 50, 45, 48, 46, 47]))
    assert result.loc[0, "Trend Consensus"] == "MIXED"
