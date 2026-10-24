import pandas as pd

from scanner.eros_regime_transition_matrix import analyze_eros_regime_transition_matrix


def _history():
    return pd.DataFrame(
        {
            "Timestamp": pd.date_range("2026-09-20 09:15", periods=6, freq="5min"),
            "Regime": [
                "RISING DOMINANT",
                "RISING DOMINANT",
                "FALLING DOMINANT",
                "FALLING DOMINANT",
                "BALANCED",
                "RISING DOMINANT",
            ],
        }
    )


def test_summarizes_regime_transitions():
    result = analyze_eros_regime_transition_matrix(_history())

    assert list(result["Transition Count"]) == [1, 1, 1]
    assert set(zip(result["Previous Regime"], result["Current Regime"], strict=True)) == {
        ("BALANCED", "RISING DOMINANT"),
        ("FALLING DOMINANT", "BALANCED"),
        ("RISING DOMINANT", "FALLING DOMINANT"),
    }
    assert round(result["Transition Share %"].sum(), 2) == 100.0


def test_empty_or_static_history_returns_empty():
    assert analyze_eros_regime_transition_matrix(None).empty
    assert analyze_eros_regime_transition_matrix(pd.DataFrame()).empty
    static = _history().copy()
    static["Regime"] = "BALANCED"
    assert analyze_eros_regime_transition_matrix(static).empty
