import pandas as pd

from scanner.eros_regime_distribution import analyze_eros_regime_distribution


def _history():
    return pd.DataFrame(
        {
            "Timestamp": pd.date_range("2026-09-20 09:15", periods=5, freq="5min"),
            "Regime": [
                "RISING DOMINANT",
                "RISING DOMINANT",
                "FALLING DOMINANT",
                "RISING DOMINANT",
                "FALLING DOMINANT",
            ],
            "Rising Breadth %": [70, 72, 35, 68, 40],
            "Falling Breadth %": [30, 28, 65, 32, 60],
            "Average Trend Confidence %": [65, 67, 72, 64, 70],
        }
    )


def test_summarizes_regime_distribution():
    result = analyze_eros_regime_distribution(_history())

    assert list(result["Regime"]) == ["RISING DOMINANT", "FALLING DOMINANT"]
    rising = result.iloc[0]
    assert rising["Snapshots"] == 3
    assert rising["Share of History %"] == 60.0
    assert rising["Average Rising Breadth %"] == 70.0
    assert rising["Average Trend Confidence %"] == 65.33


def test_deduplicates_timestamp_using_latest_row():
    history = _history().copy()
    history.loc[4, "Timestamp"] = history.loc[3, "Timestamp"]
    result = analyze_eros_regime_distribution(history)

    assert result.iloc[0]["Snapshots"] == 2
    assert result.iloc[1]["Snapshots"] == 2


def test_empty_or_invalid_history_returns_empty():
    assert analyze_eros_regime_distribution(None).empty
    assert analyze_eros_regime_distribution(pd.DataFrame()).empty
    assert analyze_eros_regime_distribution(pd.DataFrame({"Regime": ["RISING"]})).empty
