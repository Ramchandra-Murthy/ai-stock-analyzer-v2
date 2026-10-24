import pandas as pd

from scanner.eros_signal_lifecycle import analyze_eros_signal_lifecycle


def _history(scores: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Timestamp": pd.date_range("2026-09-18 10:00", periods=len(scores), freq="5min"),
            "Symbol": ["AAA"] * len(scores),
            "Exchange": ["NSE"] * len(scores),
            "Fusion Score": scores,
        }
    )


def test_eros_signal_lifecycle_accelerating():
    result = analyze_eros_signal_lifecycle(_history([60.0, 70.0, 85.0]))
    row = result.iloc[0]

    assert row["Lifecycle"] == "ACCELERATING"
    assert row["Observations"] == 3
    assert row["Fusion Change"] == 15.0
    assert row["Fusion Acceleration"] == 5.0


def test_eros_signal_lifecycle_weakening():
    result = analyze_eros_signal_lifecycle(_history([80.0, 75.0, 70.0]))

    assert result.iloc[0]["Lifecycle"] == "WEAKENING"


def test_eros_signal_lifecycle_expires_missing_current_signal():
    history = pd.concat(
        [
            _history([60.0, 70.0]),
            pd.DataFrame(
                {
                    "Timestamp": pd.to_datetime(["2026-09-18 10:00"]),
                    "Symbol": ["BBB"],
                    "Exchange": ["BSE"],
                    "Fusion Score": [65.0],
                }
            ),
        ],
        ignore_index=True,
    )
    current = pd.DataFrame({"Symbol": ["AAA"], "Exchange": ["NSE"]})

    result = analyze_eros_signal_lifecycle(history, current)

    bbb = result[result["Symbol"] == "BBB"].iloc[0]
    assert bbb["Lifecycle"] == "EXPIRED"
