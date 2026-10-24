import pandas as pd

from scanner.eros_regime_history_comparison import (
    analyze_eros_regime_history_comparison,
)


def _history():
    return pd.DataFrame(
        {
            "Timestamp": pd.date_range("2026-09-20 09:15", periods=4, freq="5min"),
            "Regime": ["RISING DOMINANT"] * 3 + ["FALLING DOMINANT"],
            "Rising Breadth %": [70, 72, 68, 35],
            "Falling Breadth %": [30, 28, 32, 65],
            "Average Trend Confidence %": [65, 67, 64, 72],
        }
    )


def test_compares_latest_regime_with_history():
    result = analyze_eros_regime_history_comparison(_history())

    assert not result.empty
    row = result.iloc[0]
    assert row["Current Regime"] == "FALLING DOMINANT"
    assert row["Previous Regime"] == "RISING DOMINANT"
    assert row["History Snapshots"] == 4
    assert row["Prior Same-Regime Snapshots"] == 0
    assert row["Current Falling Breadth %"] == 65.0


def test_uses_same_regime_history():
    history = _history().copy()
    history.loc[3, "Regime"] = "RISING DOMINANT"
    result = analyze_eros_regime_history_comparison(history)

    row = result.iloc[0]
    assert row["Prior Same-Regime Snapshots"] == 3
    assert row["Historical Same-Regime Rising Breadth %"] == 70.0


def test_empty_history_returns_empty():
    assert analyze_eros_regime_history_comparison(None).empty
    assert analyze_eros_regime_history_comparison(pd.DataFrame()).empty
