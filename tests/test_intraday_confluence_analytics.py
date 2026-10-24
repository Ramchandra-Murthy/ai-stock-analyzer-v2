import pandas as pd

from scanner.intraday_confluence_analytics import summarize_confluence_history


def test_empty_history_returns_empty():
    assert summarize_confluence_history(None).empty


def test_summary_tracks_repeated_symbols():
    history = pd.DataFrame(
        {
            "Timestamp": pd.to_datetime(
                ["2026-09-18 10:00", "2026-09-18 10:02", "2026-09-18 10:04"]
            ),
            "Symbol": ["AAA", "AAA", "BBB"],
            "Exchange": ["NSE", "NSE", "NSE"],
            "Confluence Score": [80.0, 90.0, 85.0],
        }
    )
    result = summarize_confluence_history(history)
    assert result.iloc[0]["Symbol"] == "AAA"
    assert result.iloc[0]["Observations"] == 2
    assert result.iloc[0]["Average_Score"] == 85.0
    assert result.iloc[0]["Persistence"] == "REPEATED"
