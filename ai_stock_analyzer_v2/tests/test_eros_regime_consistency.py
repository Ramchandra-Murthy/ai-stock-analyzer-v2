import pandas as pd

from scanner.eros_regime_consistency import analyze_eros_regime_consistency


def _history():
    return pd.DataFrame(
        {
            "Timestamp": pd.date_range("2026-09-20 09:15", periods=5, freq="5min"),
            "Regime": [
                "RISING DOMINANT",
                "RISING DOMINANT",
                "BALANCED",
                "FALLING DOMINANT",
                "BALANCED",
            ],
            "Rising Breadth %": [70, 55, 50, 30, 60],
            "Falling Breadth %": [30, 45, 50, 70, 40],
        }
    )


def test_compares_recorded_regime_with_breadth_implied_regime():
    result = analyze_eros_regime_consistency(_history())

    rising = result[result["Regime"] == "RISING DOMINANT"].iloc[0]
    balanced = result[result["Regime"] == "BALANCED"].iloc[0]

    assert rising["Snapshots"] == 2
    assert rising["Consistent_Snapshots"] == 1
    assert rising["Consistency %"] == 50.0
    assert balanced["Snapshots"] == 2
    assert balanced["Consistent_Snapshots"] == 1
    assert balanced["Consistency %"] == 50.0
    assert result["Overall Consistency %"].iloc[0] == 60.0


def test_invalid_input_returns_empty():
    assert analyze_eros_regime_consistency(None).empty
    assert analyze_eros_regime_consistency(pd.DataFrame()).empty
    assert analyze_eros_regime_consistency(pd.DataFrame({"Regime": ["BALANCED"]})).empty
