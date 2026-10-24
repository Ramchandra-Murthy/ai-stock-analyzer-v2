import pandas as pd

from services.price_jump_watchlist_delta import compare_watchlists


def _watchlist(rows):
    return pd.DataFrame(rows)


def test_compare_watchlists_identifies_new_up_down_and_dropped():
    previous = _watchlist(
        [
            {
                "Rank": 1,
                "Symbol": "AAA",
                "Exchange": "NSE",
                "Change over 1 min %": 3.0,
                "Day %": 4.0,
                "RVOL": 2.0,
            },
            {
                "Rank": 2,
                "Symbol": "BBB",
                "Exchange": "NSE",
                "Change over 1 min %": 2.0,
                "Day %": 3.0,
                "RVOL": 1.5,
            },
            {
                "Rank": 3,
                "Symbol": "CCC",
                "Exchange": "BSE",
                "Change over 1 min %": 1.5,
                "Day %": 2.0,
                "RVOL": 1.2,
            },
        ]
    )
    current = _watchlist(
        [
            {
                "Rank": 1,
                "Symbol": "BBB",
                "Exchange": "NSE",
                "Change over 1 min %": 2.5,
                "Day %": 3.5,
                "RVOL": 1.8,
            },
            {
                "Rank": 2,
                "Symbol": "DDD",
                "Exchange": "NSE",
                "Change over 1 min %": 2.2,
                "Day %": 2.8,
                "RVOL": 1.6,
            },
            {
                "Rank": 3,
                "Symbol": "AAA",
                "Exchange": "NSE",
                "Change over 1 min %": 1.8,
                "Day %": 4.2,
                "RVOL": 1.9,
            },
        ]
    )

    result = compare_watchlists(previous, current)

    assert dict(zip(result["Symbol"], result["Status"], strict=True)) == {
        "DDD": "NEW",
        "BBB": "UP",
        "AAA": "DOWN",
        "CCC": "DROPPED",
    }
    assert result.loc[result["Symbol"] == "BBB", "Rank change"].iloc[0] == 1
    assert result.loc[result["Symbol"] == "AAA", "Rank change"].iloc[0] == -2


def test_compare_watchlists_returns_empty_for_first_scan():
    current = _watchlist(
        [
            {
                "Rank": 1,
                "Symbol": "AAA",
                "Exchange": "NSE",
                "Change over 1 min %": 2.0,
                "Day %": 2.0,
                "RVOL": 1.5,
            }
        ]
    )

    result = compare_watchlists(None, current)

    assert result.empty
