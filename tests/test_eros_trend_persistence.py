import pandas as pd

from scanner.eros_trend_persistence import analyze_eros_trend_persistence


def _history(values: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Timestamp": pd.date_range(
                "2026-09-19 09:15",
                periods=len(values),
                freq="min",
            ),
            "Symbol": ["ABC"] * len(values),
            "Exchange": ["NSE"] * len(values),
            "Fusion Score": values,
        }
    )


def test_detects_persistent_rising_streak():
    result = analyze_eros_trend_persistence(_history([40, 42, 44, 47]))
    row = result.iloc[0]
    assert row["Direction"] == "RISING"
    assert row["Streak"] == 3
    assert row["Persistence"] == "PERSISTENT"
    assert row["Directional Consistency %"] == 100.0


def test_detects_fragile_direction():
    result = analyze_eros_trend_persistence(_history([40, 42, 41, 43]))
    assert result.loc[0, "Direction"] == "RISING"
    assert result.loc[0, "Streak"] == 1
    assert result.loc[0, "Persistence"] == "DEVELOPING"


def test_detects_stable_signal():
    result = analyze_eros_trend_persistence(_history([40, 42, 42]))
    assert result.loc[0, "Direction"] == "STABLE"
    assert result.loc[0, "Persistence"] == "STABLE"


def test_handles_new_signal():
    result = analyze_eros_trend_persistence(_history([40]))
    assert result.loc[0, "Direction"] == "NEW"
    assert result.loc[0, "Persistence"] == "INSUFFICIENT DATA"
