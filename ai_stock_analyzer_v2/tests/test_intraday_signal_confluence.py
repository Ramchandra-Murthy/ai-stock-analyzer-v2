import pandas as pd

from scanner.intraday_signal_confluence import compute_signal_confluence


def test_empty_board_returns_empty():
    assert compute_signal_confluence(pd.DataFrame()).empty


def test_confluence_rewards_multiple_confirmations():
    board = pd.DataFrame(
        {
            "Symbol": ["AAA", "BBB"],
            "Exchange": ["NSE", "NSE"],
            "2-min change %": [1.0, 0.1],
            "3-min change %": [1.2, 0.2],
            "5-min change %": [1.8, 0.3],
            "10-min change %": [2.2, 0.4],
            "15-min change %": [2.8, 0.5],
            "Volume surge x": [2.0, 1.0],
            "Breakout": ["YES", "—"],
            "Relative Strength": [1.5, -0.5],
        }
    )
    result = compute_signal_confluence(board)
    assert result.iloc[0]["Symbol"] == "AAA"
    assert result.iloc[0]["Confluence Score"] == 100.0
    assert result.iloc[0]["Confluence"] == "VERY HIGH"


def test_confluence_handles_missing_optional_columns():
    board = pd.DataFrame({"Symbol": ["AAA"], "Exchange": ["NSE"]})
    result = compute_signal_confluence(board)
    assert result.iloc[0]["Confluence Score"] == 0.0
    assert result.iloc[0]["Confluence"] == "LOW"
