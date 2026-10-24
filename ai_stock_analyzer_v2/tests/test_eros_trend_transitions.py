import pandas as pd

from scanner.eros_trend_transitions import analyze_eros_trend_transitions


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


def test_detects_reversal_to_rising():
    result = analyze_eros_trend_transitions(_history([50, 48, 51]))
    assert result.loc[0, "Trend Transition"] == "REVERSAL TO RISING"
    assert result.loc[0, "Previous Change"] == -2
    assert result.loc[0, "Fusion Change"] == 3


def test_detects_reversal_to_falling():
    result = analyze_eros_trend_transitions(_history([40, 43, 39]))
    assert result.loc[0, "Trend Transition"] == "REVERSAL TO FALLING"


def test_detects_continuing_direction():
    result = analyze_eros_trend_transitions(_history([40, 42, 45]))
    assert result.loc[0, "Trend Transition"] == "CONTINUING RISING"


def test_detects_insufficient_history():
    result = analyze_eros_trend_transitions(_history([40]))
    assert result.loc[0, "Trend Transition"] == "NEW"


def test_detects_stable_latest_change():
    result = analyze_eros_trend_transitions(_history([40, 42, 42]))
    assert result.loc[0, "Trend Transition"] == "STABLE"
