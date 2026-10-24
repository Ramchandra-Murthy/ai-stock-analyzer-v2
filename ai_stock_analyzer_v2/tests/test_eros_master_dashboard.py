import pandas as pd

from scanner import eros_master_dashboard as master_dashboard
from scanner.eros_master_dashboard import build_eros_master_dashboard


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
            "Timestamp": pd.date_range("2026-09-19 10:00", periods=4, freq="5min"),
            "Regime": ["BALANCED", "RISING DOMINANT", "RISING DOMINANT", "FALLING DOMINANT"],
            "Rising Breadth %": [70.0, 72.0, 73.0, 74.0],
            "Falling Breadth %": [30.0, 28.0, 27.0, 26.0],
            "Average Trend Confidence %": [70.0, 72.0, 73.0, 74.0],
        }
    )


def test_master_dashboard_combines_signal_and_regime_analytics():
    summary, signals = build_eros_master_dashboard(
        _history(),
        current_fusion=_history().tail(1),
        regime_history=_regime_history(),
    )

    assert not summary.empty
    assert not signals.empty
    assert summary.loc[0, "Signals"] == 1
    assert summary.loc[0, "Current Regime"] == "FALLING DOMINANT"
    assert summary.loc[0, "Regime Momentum"] == "STABLE"
    assert summary.loc[0, "Regime Transition Count"] == 2
    assert summary.loc[0, "Latest Regime Transition"] == "RISING DOMINANT → FALLING DOMINANT"
    assert summary.loc[0, "Regime Run Count"] == 3
    assert summary.loc[0, "Current Regime Duration Minutes"] == 0.0
    assert summary.loc[0, "Current Regime Average Rising Breadth %"] == 74.0
    assert summary.loc[0, "Current Regime Average Falling Breadth %"] == 26.0
    assert summary.loc[0, "Current Regime Average Trend Confidence %"] == 74.0
    assert summary.loc[0, "Current Regime Snapshots"] == 1
    assert summary.loc[0, "Regime Overall Continuation %"] == 33.33
    assert summary.loc[0, "Current Regime Run Snapshots"] == 1
    assert summary.loc[0, "Current Regime Run Duration Minutes"] == 0.0
    assert summary.loc[0, "Current Regime Average Run Snapshots"] == 1.0
    assert "Lifecycle" in signals.columns
    assert "Confidence" in signals.columns


def test_master_dashboard_empty_history():
    summary, signals = build_eros_master_dashboard(None)
    assert summary.empty
    assert signals.empty


def test_master_dashboard_accepts_history_without_regime_history():
    summary, signals = build_eros_master_dashboard(_history())
    assert summary.loc[0, "Signals"] == 1
    assert not signals.empty


def test_master_dashboard_handles_all_null_alignment_percent(monkeypatch):
    alignment = pd.DataFrame(
        {
            "Symbol": ["AAA"],
            "Exchange": ["NSE"],
            "Alignment %": pd.Series([pd.NA], dtype="Float64"),
        }
    )
    monkeypatch.setattr(master_dashboard, "analyze_eros_signal_alignment", lambda *_args: alignment)

    summary, signals = build_eros_master_dashboard(_history())

    assert summary.loc[0, "Average Signal Alignment %"] is None
    assert not signals.empty
