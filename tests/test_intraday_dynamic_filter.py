"""Tests for dynamic intraday candidate filtering."""

import pandas as pd

from services.intraday_dynamic_filter import filter_intraday_candidates


def test_filters_and_sorts_current_candidates():
    results = pd.DataFrame(
        [
            {
                "Symbol": "A",
                "Direction": "LONG",
                "Plan state": "TRIGGERED",
                "Exchange": "NSE",
                "Composite score": 80,
                "Opportunity score": 70,
                "5-min change %": 2,
            },
            {
                "Symbol": "B",
                "Direction": "SHORT",
                "Plan state": "WATCH",
                "Exchange": "NSE",
                "Composite score": 90,
                "Opportunity score": 80,
                "5-min change %": 3,
            },
            {
                "Symbol": "C",
                "Direction": "LONG",
                "Plan state": "TRIGGERED",
                "Exchange": "BSE",
                "Composite score": 95,
                "Opportunity score": 85,
                "5-min change %": 4,
            },
        ]
    )

    filtered = filter_intraday_candidates(
        results,
        direction="LONG",
        setup_state="TRIGGERED",
        exchange="NSE",
        minimum_score=75,
        limit=10,
    )

    assert list(filtered["Symbol"]) == ["A"]


def test_empty_results_are_stable():
    results = pd.DataFrame(columns=["Symbol", "Composite score"])

    filtered = filter_intraday_candidates(results)

    assert filtered.empty
    assert list(filtered.columns) == ["Symbol", "Composite score"]
