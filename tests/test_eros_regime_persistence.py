import pandas as pd

from scanner.eros_regime_persistence import analyze_eros_regime_persistence


def _history(regimes):
    return pd.DataFrame(
        {
            "Timestamp": pd.date_range("2026-09-20 09:15", periods=len(regimes), freq="5min"),
            "Regime": regimes,
        }
    )


def test_summarizes_regime_persistence():
    result = analyze_eros_regime_persistence(
        _history(
            [
                "BALANCED",
                "BALANCED",
                "RISING DOMINANT",
                "RISING DOMINANT",
                "RISING DOMINANT",
                "BALANCED",
            ]
        )
    )

    balanced = result[result["Regime"] == "BALANCED"].iloc[0]
    rising = result[result["Regime"] == "RISING DOMINANT"].iloc[0]

    assert balanced["Runs"] == 2
    assert balanced["Total_Snapshots"] == 3
    assert balanced["Average_Run_Snapshots"] == 1.5
    assert balanced["Maximum_Run_Snapshots"] == 2
    assert balanced["Average_Duration_Minutes"] == 2.5
    assert balanced["Current Run"]
    assert balanced["Current Run Snapshots"] == 1

    assert rising["Runs"] == 1
    assert rising["Maximum_Run_Snapshots"] == 3
    assert rising["Maximum_Duration_Minutes"] == 10.0
    assert not rising["Current Run"]

    assert balanced["Overall Continuation %"] == 60.0


def test_invalid_input_returns_empty():
    assert analyze_eros_regime_persistence(None).empty
    assert analyze_eros_regime_persistence(pd.DataFrame()).empty
    assert analyze_eros_regime_persistence(pd.DataFrame({"Regime": ["BALANCED"]})).empty
