import pandas as pd

from scanner.eros_regime_duration import analyze_eros_regime_duration


def _history(regimes):
    return pd.DataFrame(
        {
            "Timestamp": pd.date_range("2026-09-20 09:15", periods=len(regimes), freq="5min"),
            "Regime": regimes,
        }
    )


def test_measures_contiguous_regime_durations():
    result = analyze_eros_regime_duration(
        _history(
            [
                "BALANCED",
                "BALANCED",
                "RISING DOMINANT",
                "RISING DOMINANT",
                "RISING DOMINANT",
                "FALLING DOMINANT",
            ]
        )
    )

    assert result["Regime"].tolist() == [
        "BALANCED",
        "RISING DOMINANT",
        "FALLING DOMINANT",
    ]
    assert result["Snapshots"].tolist() == [2, 3, 1]
    assert result["Duration Minutes"].tolist() == [5.0, 10.0, 0.0]
    assert result["Is Current"].tolist() == [False, False, True]


def test_repeated_regimes_create_separate_runs():
    result = analyze_eros_regime_duration(
        _history(["RISING DOMINANT", "FALLING DOMINANT", "RISING DOMINANT"])
    )
    assert result["Run Number"].tolist() == [1, 2, 3]
    assert result["Regime"].tolist() == [
        "RISING DOMINANT",
        "FALLING DOMINANT",
        "RISING DOMINANT",
    ]


def test_invalid_input_returns_empty():
    assert analyze_eros_regime_duration(None).empty
    assert analyze_eros_regime_duration(pd.DataFrame()).empty
    assert analyze_eros_regime_duration(pd.DataFrame({"Regime": ["BALANCED"]})).empty
