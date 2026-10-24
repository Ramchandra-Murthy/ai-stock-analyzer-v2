import pandas as pd

from scanner.eros_regime_signal_sync import analyze_eros_regime_signal_sync


def _history():
    return pd.DataFrame(
        {
            "Timestamp": pd.date_range("2026-09-19 10:00", periods=4, freq="5min"),
            "Symbol": ["AAA"] * 4,
            "Exchange": ["NSE"] * 4,
            "Fusion Score": [50.0, 60.0, 70.0, 80.0],
        }
    )


def _regime_history():
    return pd.DataFrame(
        {
            "Timestamp": pd.date_range("2026-09-19 10:00", periods=3, freq="5min"),
            "Regime": ["RISING DOMINANT"] * 3,
        }
    )


def test_regime_signal_sync_detects_aligned_signal():
    result = analyze_eros_regime_signal_sync(
        _history(),
        _regime_history(),
        _history().tail(1),
    )

    assert not result.empty
    assert result.loc[0, "Current Regime"] == "RISING DOMINANT"
    assert result.loc[0, "Regime Direction"] == "RISING"
    assert result.loc[0, "Regime-Signal Sync"] == "ALIGNED"


def test_regime_signal_sync_requires_regime_history():
    assert analyze_eros_regime_signal_sync(_history(), None).empty
