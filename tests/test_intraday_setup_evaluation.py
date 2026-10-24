"""Tests for intraday setup evaluation statistics."""

import pandas as pd

from services.intraday_setup_evaluation import setup_statistics


def test_summarizes_observed_setup_outcomes():
    outcomes = {
        "A": {"State": "TRIGGERED", "Price change %": 2.0},
        "B": {"State": "TRIGGERED", "Price change %": -1.0},
        "C": {"State": "TRIGGERED", "Price change %": 0.0},
        "D": {"State": "WATCH", "Price change %": 1.0},
    }

    frame = setup_statistics(outcomes)

    triggered = frame.loc[frame["State"] == "TRIGGERED"].iloc[0]
    assert triggered["Setups"] == 3
    assert triggered["Positive outcomes"] == 1
    assert triggered["Negative outcomes"] == 1
    assert triggered["Flat outcomes"] == 1
    assert triggered["Positive rate %"] == 33.33
    assert triggered["Average change %"] == 0.33


def test_empty_statistics_has_stable_columns():
    frame = setup_statistics({})

    assert isinstance(frame, pd.DataFrame)
    assert list(frame.columns) == [
        "State",
        "Setups",
        "Positive outcomes",
        "Negative outcomes",
        "Flat outcomes",
        "Positive rate %",
        "Average change %",
        "Best change %",
        "Worst change %",
    ]
