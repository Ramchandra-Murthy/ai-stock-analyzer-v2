import pandas as pd

from scanner.price_jump_history_analytics import summarize_price_jump_history


def test_empty_history_returns_empty_summary():
    assert summarize_price_jump_history(pd.DataFrame()).empty


def test_summary_counts_repeated_observations():
    history = pd.DataFrame(
        [
            {
                "Timestamp": "2026-09-18 09:20",
                "Symbol": "TCS",
                "Exchange": "NSE",
                "Change over 5 min %": 1.0,
            },
            {
                "Timestamp": "2026-09-18 09:25",
                "Symbol": "TCS",
                "Exchange": "NSE",
                "Change over 5 min %": 2.0,
            },
            {
                "Timestamp": "2026-09-18 09:25",
                "Symbol": "INFY",
                "Exchange": "NSE",
                "Change over 5 min %": 1.5,
            },
        ]
    )

    result = summarize_price_jump_history(history)

    assert len(result) == 2
    assert result.iloc[0]["Symbol"] == "TCS"
    assert result.iloc[0]["Observations"] == 2
    assert result.iloc[0]["Average_Change"] == 1.5
    assert result.iloc[0]["Peak_Change"] == 2.0
    assert result.iloc[0]["Persistence"] == "REPEATED"


def test_summary_ignores_invalid_change_values():
    history = pd.DataFrame(
        [
            {
                "Timestamp": "2026-09-18 09:20",
                "Symbol": "INFY",
                "Exchange": "NSE",
                "Change over 5 min %": "bad",
            }
        ]
    )
    assert summarize_price_jump_history(history).empty
