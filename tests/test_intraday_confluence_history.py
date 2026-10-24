from datetime import datetime

import pandas as pd

from scanner.intraday_confluence_history import append_confluence_snapshot


def test_empty_inputs_are_safe():
    assert append_confluence_snapshot(None, datetime(2026, 9, 18, 10, 0), pd.DataFrame()).empty


def test_only_high_confluence_rows_are_recorded():
    board = pd.DataFrame(
        {
            "Symbol": ["AAA", "BBB"],
            "Exchange": ["NSE", "NSE"],
            "Confluence Score": [80.0, 60.0],
            "Confluence": ["VERY HIGH", "HIGH"],
            "Sector": ["IT", "IT"],
            "Price": [100.0, 90.0],
        }
    )
    result = append_confluence_snapshot(None, datetime(2026, 9, 18, 10, 0), board)
    assert len(result) == 1
    assert result.iloc[0]["Symbol"] == "AAA"
    assert result.iloc[0]["Confluence Score"] == 80.0


def test_duplicate_snapshot_is_replaced():
    timestamp = datetime(2026, 9, 18, 10, 0)
    board = pd.DataFrame(
        {
            "Symbol": ["AAA"],
            "Exchange": ["NSE"],
            "Confluence Score": [80.0],
            "Confluence": ["VERY HIGH"],
        }
    )
    first = append_confluence_snapshot(None, timestamp, board)
    second = append_confluence_snapshot(
        first, timestamp, board.assign(**{"Confluence Score": [90.0]})
    )
    assert len(second) == 1
    assert second.iloc[0]["Confluence Score"] == 90.0
