import pandas as pd

from scanner.eros_signal_alignment import analyze_eros_signal_alignment


def _history():
    return pd.DataFrame(
        {
            "Timestamp": pd.date_range("2026-09-19 10:00", periods=4, freq="5min"),
            "Symbol": ["AAA"] * 4,
            "Exchange": ["NSE"] * 4,
            "Fusion Score": [50.0, 60.0, 70.0, 80.0],
        }
    )


def test_signal_alignment_returns_descriptive_diagnostics():
    result = analyze_eros_signal_alignment(_history(), _history().tail(1))

    assert not result.empty
    assert result.loc[0, "Symbol"] == "AAA"
    assert result.loc[0, "Directional Diagnostics"] >= 1
    assert 0.0 <= result.loc[0, "Alignment %"] <= 100.0
    assert "Alignment %" in result.columns
    assert "Alignment" in result.columns


def test_signal_alignment_handles_empty_history():
    result = analyze_eros_signal_alignment(None)
    assert result.empty
