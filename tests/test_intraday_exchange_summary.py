"""Tests for exchange-level intraday summaries."""

import pandas as pd

from services.intraday_exchange_summary import exchange_summary


def test_exchange_summary_groups_nse_and_bse():
    frame = pd.DataFrame(
        [
            {"Exchange": "NSE", "5-min change %": 1.0, "Volume surge x": 2.0},
            {"Exchange": "NSE", "5-min change %": -0.5, "Volume surge x": 1.5},
            {"Exchange": "BSE", "5-min change %": 0.5, "Volume surge x": 1.2},
        ]
    )

    summary = exchange_summary(frame)

    assert list(summary["Exchange"]) == ["BSE", "NSE"]
    assert summary.loc[summary["Exchange"] == "NSE", "Candidates"].iloc[0] == 2
    assert summary.loc[summary["Exchange"] == "BSE", "Positive change %"].iloc[0] == 100.0
    assert summary.loc[summary["Exchange"] == "NSE", "Positive change %"].iloc[0] == 50.0


def test_exchange_summary_empty_frame_has_stable_columns():
    summary = exchange_summary(pd.DataFrame())

    assert summary.empty
    assert list(summary.columns) == [
        "Exchange",
        "Candidates",
        "Average change %",
        "Average volume surge x",
        "Positive change %",
    ]
