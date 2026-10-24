import pandas as pd

from scanner import eros_signal_alignment


def test_alignment_percentage_is_numeric_when_directional_diagnostics_are_nullable(monkeypatch):
    confidence = pd.DataFrame(
        [
            {
                "Symbol": "RELIANCE",
                "Exchange": "NSE",
                "Timestamp": pd.Timestamp("2026-10-07 09:30"),
                "Fusion Score": 72.0,
                "Trend Consensus": "RISING CONFIRMED",
                "Direction": "RISING",
                "Trend Quality": "STRONG",
                "Trend Confidence %": 81.0,
                "Confidence": 72.0,
            },
            {
                "Symbol": "TCS",
                "Exchange": "NSE",
                "Timestamp": pd.Timestamp("2026-10-07 09:30"),
                "Fusion Score": 48.0,
                "Trend Consensus": "NEUTRAL",
                "Direction": "NEUTRAL",
                "Trend Quality": "WEAK",
                "Trend Confidence %": 48.0,
                "Confidence": 52.0,
            },
        ]
    )
    lifecycle = pd.DataFrame(
        [
            {
                "Symbol": "RELIANCE",
                "Exchange": "NSE",
                "Lifecycle": "ACCELERATING",
                "Fusion Change": 2.0,
                "Fusion Acceleration": 0.5,
                "Trend": "RISING",
            },
            {
                "Symbol": "TCS",
                "Exchange": "NSE",
                "Lifecycle": "STABLE",
                "Fusion Change": 0.0,
                "Fusion Acceleration": 0.0,
                "Trend": "NEUTRAL",
            },
        ]
    )

    monkeypatch.setattr(
        eros_signal_alignment,
        "analyze_eros_trend_confidence",
        lambda history, current_fusion: confidence,
    )
    monkeypatch.setattr(
        eros_signal_alignment,
        "analyze_eros_signal_lifecycle",
        lambda history, current_fusion: lifecycle,
    )

    result = eros_signal_alignment.analyze_eros_signal_alignment(None)

    assert result["Alignment %"].iloc[0] == 100.0
    assert pd.isna(result["Alignment %"].iloc[1])
    assert str(result["Alignment %"].dtype) == "Float64"
