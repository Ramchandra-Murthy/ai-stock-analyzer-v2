import pandas as pd

from scanner.eros_regime_breadth import analyze_eros_regime_breadth


def _history():
    return pd.DataFrame(
        {
            "Timestamp": pd.date_range("2026-09-20 09:15", periods=6, freq="5min"),
            "Regime": [
                "RISING DOMINANT",
                "RISING DOMINANT",
                "BALANCED",
                "BALANCED",
                "FALLING DOMINANT",
                "RISING DOMINANT",
            ],
            "Rising Breadth %": [70, 80, 50, 40, 20, 90],
            "Average Trend Confidence %": [60, 70, 50, 40, 80, 90],
        }
    )


def test_summarizes_breadth_by_regime():
    """Verify descriptive breadth statistics for each aggregate regime."""
    result = analyze_eros_regime_breadth(_history())

    rising = result[result["Regime"] == "RISING DOMINANT"].iloc[0]
    balanced = result[result["Regime"] == "BALANCED"].iloc[0]

    assert rising["Snapshots"] == 3
    assert rising["Average_Rising_Breadth"] == 80.0
    assert rising["Average Falling Breadth"] == 20.0
    assert rising["Minimum_Rising_Breadth"] == 70.0
    assert rising["Maximum_Rising_Breadth"] == 90.0
    assert rising["Average_Trend_Confidence"] == 73.33
    assert rising["Session Share %"] == 50.0
    assert balanced["Average_Rising_Breadth"] == 45.0


def test_invalid_input_returns_empty():
    assert analyze_eros_regime_breadth(None).empty
    assert analyze_eros_regime_breadth(pd.DataFrame()).empty
    assert analyze_eros_regime_breadth(pd.DataFrame({"Regime": ["BALANCED"]})).empty
