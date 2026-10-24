import pandas as pd

from scanner.eros_regime_recency import analyze_eros_regime_recency


def _history():
    return pd.DataFrame(
        {
            "Timestamp": pd.date_range("2026-09-20 09:15", periods=5, freq="5min"),
            "Regime": [
                "RISING DOMINANT",
                "RISING DOMINANT",
                "RISING DOMINANT",
                "FALLING DOMINANT",
                "FALLING DOMINANT",
            ],
        }
    )


def test_summarizes_current_regime_recency():
    result = analyze_eros_regime_recency(_history())

    row = result.iloc[0]
    assert row["Current Regime"] == "FALLING DOMINANT"
    assert row["Current Run Snapshots"] == 2
    assert row["Current Run Duration Minutes"] == 5.0
    assert row["Previous Regime"] == "RISING DOMINANT"
    assert row["Historical Transitions"] == 1


def test_empty_history_returns_empty():
    assert analyze_eros_regime_recency(None).empty
    assert analyze_eros_regime_recency(pd.DataFrame()).empty
