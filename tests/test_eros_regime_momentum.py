import pandas as pd

from scanner.eros_regime_momentum import analyze_eros_regime_momentum


def _history(
    rising: list[float],
    falling: list[float],
    confidence: list[float],
    regimes: list[str],
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Timestamp": pd.date_range("2026-01-01 09:15", periods=len(rising), freq="5min"),
            "Rising Breadth %": rising,
            "Falling Breadth %": falling,
            "Average Trend Confidence %": confidence,
            "Regime": regimes,
        }
    )


def test_rising_strength():
    result = analyze_eros_regime_momentum(
        _history(
            [50.0, 58.0],
            [50.0, 42.0],
            [60.0, 65.0],
            ["BALANCED", "RISING DOMINANT"],
        )
    )

    row = result.iloc[0]
    assert row["Regime Momentum"] == "RISING STRENGTH"
    assert row["Rising Breadth Δ"] == 8.0
    assert row["Confidence Δ"] == 5.0


def test_falling_strength():
    result = analyze_eros_regime_momentum(
        _history(
            [70.0, 62.0],
            [30.0, 38.0],
            [70.0, 66.0],
            ["RISING DOMINANT", "BALANCED"],
        )
    )

    assert result.loc[0, "Regime Momentum"] == "RISING WEAKNESS"


def test_stable_and_initial_states():
    initial = analyze_eros_regime_momentum(_history([50.0], [50.0], [60.0], ["BALANCED"]))
    stable = analyze_eros_regime_momentum(
        _history([50.0, 51.0], [50.0, 49.0], [60.0, 61.0], ["BALANCED", "BALANCED"])
    )

    assert initial.loc[0, "Regime Momentum"] == "INITIAL"
    assert stable.loc[0, "Regime Momentum"] == "STABLE"


def test_invalid_input_returns_empty():
    assert analyze_eros_regime_momentum(None).empty
    assert analyze_eros_regime_momentum(pd.DataFrame()).empty
    assert analyze_eros_regime_momentum(pd.DataFrame({"Regime": ["BALANCED"]})).empty
