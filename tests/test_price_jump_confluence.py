import pandas as pd

from scanner.price_jump_confluence import match_price_jumps_to_confluence


def test_empty_inputs_return_empty():
    assert match_price_jumps_to_confluence(pd.DataFrame(), pd.DataFrame()).empty


def test_price_jump_gets_confluence_confirmation():
    jumps = pd.DataFrame(
        {
            "Symbol": ["AAA", "BBB"],
            "Exchange": ["NSE", "NSE"],
            "Last price": [100.0, 90.0],
        }
    )
    board = pd.DataFrame(
        {
            "Symbol": ["AAA", "BBB"],
            "Exchange": ["NSE", "NSE"],
            "Confluence Score": [85.0, 60.0],
            "Confluence": ["VERY HIGH", "HIGH"],
            "Relative Strength": [2.0, -1.0],
            "Volume surge x": [2.0, 1.0],
            "Breakout": ["YES", "—"],
        }
    )
    result = match_price_jumps_to_confluence(jumps, board)
    assert result.iloc[0]["Symbol"] == "AAA"
    assert bool(result.iloc[0]["Confluence Confirmation"]) is True
    assert bool(result.iloc[1]["Confluence Confirmation"]) is False
