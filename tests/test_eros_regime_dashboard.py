import pandas as pd

from scanner.eros_regime_dashboard import build_eros_regime_dashboard_snapshot


def _history():
    return pd.DataFrame(
        {
            "Timestamp": pd.date_range("2026-09-20 09:15", periods=4, freq="5min"),
            "Regime": ["RISING DOMINANT"] * 4,
            "Rising Breadth %": [70, 72, 68, 75],
            "Falling Breadth %": [30, 28, 32, 25],
            "Average Trend Confidence %": [65, 67, 64, 70],
        }
    )


def test_builds_descriptive_regime_snapshot():
    result = build_eros_regime_dashboard_snapshot(_history())

    assert not result.empty
    row = result.iloc[0]
    assert row["Current Regime"] == "RISING DOMINANT"
    assert row["Latest Breadth Strength"] == 50.0
    assert row["Current Duration Snapshots"] == 4
    assert row["Average Rising Breadth %"] == 71.25
    assert row["Average Falling Breadth %"] == 28.75


def test_empty_history_returns_empty():
    assert build_eros_regime_dashboard_snapshot(None).empty
    assert build_eros_regime_dashboard_snapshot(pd.DataFrame()).empty
