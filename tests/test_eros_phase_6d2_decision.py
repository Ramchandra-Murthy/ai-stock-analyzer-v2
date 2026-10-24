"""Phase 6D.2 EROS decision-stage integration validation."""

import pandas as pd

from scanner.eros_regime_signal_sync import analyze_eros_regime_signal_sync
from scanner.eros_signal_alignment import analyze_eros_signal_alignment
from scanner.eros_signal_lifecycle import analyze_eros_signal_lifecycle
from scanner.eros_trend_confidence import analyze_eros_trend_confidence
from scanner.eros_trend_regime import analyze_eros_trend_regime


def _fusion_history() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Timestamp": pd.date_range("2026-09-25 10:00", periods=6, freq="5min"),
            "Symbol": ["AAA"] * 6,
            "Exchange": ["NSE"] * 6,
            "Fusion Score": [50.0, 55.0, 60.0, 65.0, 70.0, 75.0],
        }
    )


def _current_fusion() -> pd.DataFrame:
    return _fusion_history().tail(1)


def _regime_history() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Timestamp": pd.date_range("2026-09-25 10:00", periods=3, freq="5min"),
            "Regime": ["RISING DOMINANT"] * 3,
            "Rising Breadth %": [80.0, 82.0, 84.0],
            "Falling Breadth %": [20.0, 18.0, 16.0],
            "Average Trend Confidence %": [80.0, 82.0, 84.0],
        }
    )


def test_phase_6d2_decision_stage_is_coherent_end_to_end():
    history = _fusion_history()
    current = _current_fusion()
    regime_history = _regime_history()

    lifecycle = analyze_eros_signal_lifecycle(history, current)
    confidence = analyze_eros_trend_confidence(history, current)
    alignment = analyze_eros_signal_alignment(history, current)
    trend_regime = analyze_eros_trend_regime(confidence)
    regime_sync = analyze_eros_regime_signal_sync(history, regime_history, current)

    assert lifecycle.loc[0, "Lifecycle"] == "PERSISTENT"
    assert confidence.loc[0, "Trend Consensus"] == "RISING CONFIRMED"
    assert confidence.loc[0, "Confidence"] == "HIGH"
    assert confidence.loc[0, "Trend Confidence %"] == 100.0

    assert alignment.loc[0, "Alignment"] == "ALIGNED"
    assert alignment.loc[0, "Alignment %"] == 100.0

    assert trend_regime.loc[0, "Regime"] == "RISING DOMINANT"
    assert trend_regime.loc[0, "Rising Breadth %"] == 100.0

    assert regime_sync.loc[0, "Regime Direction"] == "RISING"
    assert regime_sync.loc[0, "Signal Direction"] == "RISING"
    assert regime_sync.loc[0, "Regime-Signal Sync"] == "ALIGNED"
