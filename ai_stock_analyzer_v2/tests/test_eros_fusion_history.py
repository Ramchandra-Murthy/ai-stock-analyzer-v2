import pandas as pd

from scanner.eros_fusion_history import append_eros_fusion_snapshot
from scanner.eros_fusion_history_analytics import summarize_eros_fusion_history


def test_append_eros_fusion_snapshot_is_bounded_and_deduplicated():
    fusion = pd.DataFrame(
        {
            "Symbol": ["AAA"],
            "Exchange": ["NSE"],
            "Fusion Score": [82.5],
            "Fusion Coverage": [4],
        }
    )
    timestamp = pd.Timestamp("2026-09-18 10:00").to_pydatetime()

    first = append_eros_fusion_snapshot(None, timestamp, fusion)
    second = append_eros_fusion_snapshot(first, timestamp, fusion)

    assert len(second) == 1
    assert second.iloc[0]["Fusion Score"] == 82.5


def test_summarize_eros_fusion_history_tracks_persistence():
    history = pd.DataFrame(
        {
            "Timestamp": pd.to_datetime(
                ["2026-09-18 10:00", "2026-09-18 10:05", "2026-09-18 10:10"]
            ),
            "Symbol": ["AAA", "AAA", "AAA"],
            "Exchange": ["NSE", "NSE", "NSE"],
            "Fusion Score": [70.0, 80.0, 90.0],
        }
    )

    result = summarize_eros_fusion_history(history)

    assert result.iloc[0]["Observations"] == 3
    assert result.iloc[0]["Latest_Fusion"] == 90.0
    assert result.iloc[0]["Persistence"] == "PERSISTENT"
