import pandas as pd

from scanner.eros_regime_transition_intervals import (
    analyze_eros_regime_transition_intervals,
)


def _history():
    return pd.DataFrame(
        {
            "Timestamp": pd.date_range("2026-09-20 09:15", periods=7, freq="5min"),
            "Regime": [
                "RISING DOMINANT",
                "RISING DOMINANT",
                "FALLING DOMINANT",
                "FALLING DOMINANT",
                "BALANCED",
                "BALANCED",
                "RISING DOMINANT",
            ],
        }
    )


def test_calculates_transition_intervals():
    result = analyze_eros_regime_transition_intervals(_history())

    assert list(result["Transition Count"]) == [1, 2, 3]
    assert pd.isna(result.iloc[0]["Minutes Since Previous Transition"])
    assert list(result["Minutes Since Previous Transition"].iloc[1:]) == [10.0, 10.0]
    assert result.iloc[2]["Transition"] == "BALANCED → RISING DOMINANT"


def test_empty_or_static_history_returns_empty():
    assert analyze_eros_regime_transition_intervals(None).empty
    assert analyze_eros_regime_transition_intervals(pd.DataFrame()).empty
    static = _history().copy()
    static["Regime"] = "BALANCED"
    assert analyze_eros_regime_transition_intervals(static).empty
