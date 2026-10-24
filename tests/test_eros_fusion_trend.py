import pandas as pd

from scanner.eros_fusion_trend import analyze_eros_fusion_trend


def test_analyze_eros_fusion_trend_tracks_change_and_acceleration():
    history = pd.DataFrame(
        {
            "Timestamp": pd.to_datetime(
                ["2026-09-18 10:00", "2026-09-18 10:05", "2026-09-18 10:10"]
            ),
            "Symbol": ["AAA", "AAA", "AAA"],
            "Exchange": ["NSE", "NSE", "NSE"],
            "Fusion Score": [70.0, 80.0, 95.0],
        }
    )

    result = analyze_eros_fusion_trend(history)

    assert len(result) == 1
    assert result.iloc[0]["Fusion Score"] == 95.0
    assert result.iloc[0]["Fusion Change"] == 15.0
    assert result.iloc[0]["Fusion Acceleration"] == 5.0
    assert result.iloc[0]["Trend"] == "RISING"


def test_analyze_eros_fusion_trend_marks_decline():
    history = pd.DataFrame(
        {
            "Timestamp": pd.to_datetime(["2026-09-18 10:00", "2026-09-18 10:05"]),
            "Symbol": ["BBB", "BBB"],
            "Exchange": ["BSE", "BSE"],
            "Fusion Score": [90.0, 75.0],
        }
    )

    result = analyze_eros_fusion_trend(history)

    assert result.iloc[0]["Fusion Change"] == -15.0
    assert result.iloc[0]["Fusion Acceleration"] == -15.0
    assert result.iloc[0]["Trend"] == "FALLING"
