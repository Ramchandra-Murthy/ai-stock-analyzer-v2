"""Tests for intraday scan snapshot deltas."""

from services.intraday_scan_delta import snapshot_delta_frame


def test_snapshot_delta_tracks_candidate_and_metric_changes():
    history = [
        {
            "Timestamp": "2026-09-21T12:00:00+05:30",
            "Candidates": 10,
            "Average change %": 0.75,
            "Average volume surge x": 1.5,
            "Exchanges": "NSE",
            "Market-cap baskets": "Large cap",
            "Top symbols": "AAA, BBB",
        },
        {
            "Timestamp": "2026-09-21T12:05:00+05:30",
            "Candidates": 12,
            "Average change %": 1.25,
            "Average volume surge x": 2.0,
            "Exchanges": "NSE",
            "Market-cap baskets": "Large cap",
            "Top symbols": "BBB, CCC",
        },
    ]

    frame = snapshot_delta_frame(history)

    assert frame.iloc[0]["Candidate delta"] == 2
    assert frame.iloc[0]["Average change delta %"] == 0.5
    assert frame.iloc[0]["Average volume surge delta x"] == 0.5
    assert frame.iloc[0]["Exchanges"] == "NSE"
    assert frame.iloc[0]["Market-cap baskets"] == "Large cap"
    assert frame.iloc[0]["New top symbols"] == "CCC"
    assert frame.iloc[0]["Dropped top symbols"] == "AAA"


def test_snapshot_delta_requires_two_snapshots():
    frame = snapshot_delta_frame(
        [
            {
                "Timestamp": "2026-09-21T12:00:00+05:30",
                "Candidates": 10,
            }
        ]
    )

    assert frame.empty
    assert list(frame.columns) == [
        "Timestamp",
        "Candidate delta",
        "Average change delta %",
        "Average volume surge delta x",
        "Exchanges",
        "Market-cap baskets",
        "New top symbols",
        "Dropped top symbols",
    ]
