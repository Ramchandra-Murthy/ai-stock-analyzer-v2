import pandas as pd

from scanner.eros_regime_stability import analyze_eros_regime_stability


def _history(regimes, breadth, confidence):
    return pd.DataFrame(
        {
            "Timestamp": pd.date_range("2026-01-01 09:15", periods=len(regimes), freq="5min"),
            "Regime": regimes,
            "Rising Breadth %": breadth,
            "Falling Breadth %": [100 - value for value in breadth],
            "Average Trend Confidence %": confidence,
        }
    )


def test_high_stability():
    result = analyze_eros_regime_stability(
        _history(
            ["RISING DOMINANT"] * 5,
            [70, 72, 71, 74, 73],
            [70, 72, 71, 74, 73],
        )
    )
    row = result.iloc[0]
    assert row["Stability"] == "HIGH"
    assert row["Regime Streak"] == 5


def test_moderate_stability():
    result = analyze_eros_regime_stability(
        _history(
            ["BALANCED"] * 3,
            [45, 55, 50],
            [55, 65, 60],
        )
    )
    assert result.loc[0, "Stability"] == "MODERATE"


def test_low_or_initial_stability():
    low = analyze_eros_regime_stability(
        _history(["RISING DOMINANT", "RISING DOMINANT"], [60, 85], [60, 90])
    )
    initial = analyze_eros_regime_stability(_history(["BALANCED"], [50], [60]))
    assert low.loc[0, "Stability"] == "LOW"
    assert initial.loc[0, "Stability"] == "INITIAL"


def test_invalid_input_returns_empty():
    assert analyze_eros_regime_stability(None).empty
    assert analyze_eros_regime_stability(pd.DataFrame()).empty
    assert analyze_eros_regime_stability(pd.DataFrame({"Regime": ["BALANCED"]})).empty
