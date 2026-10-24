import pandas as pd

from scanner.eros_signal_lifecycle_transitions import (
    analyze_eros_signal_lifecycle_transitions,
)


def _history(symbol, scores):
    return pd.DataFrame(
        {
            "Timestamp": pd.date_range("2026-09-18 10:00", periods=len(scores), freq="5min"),
            "Symbol": [symbol] * len(scores),
            "Exchange": ["NSE"] * len(scores),
            "Fusion Score": scores,
        }
    )


def test_lifecycle_transition_reports_initial_and_age():
    result = analyze_eros_signal_lifecycle_transitions(_history("AAA", [60.0, 70.0, 85.0]))
    row = result.iloc[0]

    assert row["Lifecycle"] == "ACCELERATING"
    assert row["Previous Lifecycle"] == "CONFIRMED"
    assert row["Lifecycle Transition"] == "CONFIRMED → ACCELERATING"
    assert row["Lifecycle Age"] == 3
    assert row["Transition Count"] == 2


def test_lifecycle_transition_handles_multiple_symbols():
    history = pd.concat(
        [
            _history("AAA", [60.0, 70.0]),
            _history("BBB", [80.0, 75.0]),
        ],
        ignore_index=True,
    )
    result = analyze_eros_signal_lifecycle_transitions(history)

    assert set(result["Symbol"]) == {"AAA", "BBB"}
    assert result.loc[result["Symbol"] == "BBB", "Lifecycle"].iloc[0] == "WEAKENING"


def test_invalid_input_returns_empty():
    assert analyze_eros_signal_lifecycle_transitions(None).empty
    assert analyze_eros_signal_lifecycle_transitions(pd.DataFrame()).empty
    assert analyze_eros_signal_lifecycle_transitions(pd.DataFrame({"Symbol": ["AAA"]})).empty
