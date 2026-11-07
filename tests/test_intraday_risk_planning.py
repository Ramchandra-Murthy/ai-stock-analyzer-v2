"""Tests for intraday risk and trade-planning metrics."""

import pandas as pd

from services.intraday_risk_planning import risk_plan_frame


def test_calculates_risk_and_capital_limited_quantity():
    results = pd.DataFrame(
        [
            {
                "Symbol": "A",
                "Price": 100.0,
                "Entry reference": 100.0,
                "Stop reference": 98.0,
                "Risk per share": 2.0,
            }
        ]
    )

    frame = risk_plan_frame(results, risk_budget=1000, capital_limit=10000)

    assert frame.loc[0, "Risk-based quantity"] == 500
    assert frame.loc[0, "Capital-based quantity"] == 100
    assert frame.loc[0, "Suggested quantity"] == 100
    assert frame.loc[0, "Planned capital"] == 10000
    assert frame.loc[0, "Planned risk"] == 200


def test_empty_risk_plan_has_stable_columns():
    frame = risk_plan_frame(pd.DataFrame(columns=["Symbol"]))

    assert "Suggested quantity" in frame.columns
    assert frame.empty


import numpy as np
import pytest


@pytest.mark.parametrize("budget", [float("nan"), float("inf"), -1])
def test_rejects_invalid_risk_budget(budget):
    with pytest.raises(ValueError, match="risk_budget"):
        risk_plan_frame(pd.DataFrame([{"Price": 100.0, "Risk per share": 2.0}]), risk_budget=budget)


@pytest.mark.parametrize("limit", [float("nan"), float("-inf"), -1])
def test_rejects_invalid_capital_limit(limit):
    with pytest.raises(ValueError, match="capital_limit"):
        risk_plan_frame(pd.DataFrame([{"Price": 100.0, "Risk per share": 2.0}]), capital_limit=limit)


def test_invalid_row_prices_and_risk_fail_closed_to_zero_quantity():
    results = pd.DataFrame(
        [
            {"Symbol": "BAD_PRICE", "Price": np.inf, "Risk per share": 2.0},
            {"Symbol": "BAD_RISK", "Price": 100.0, "Risk per share": np.nan},
            {"Symbol": "ZERO_RISK", "Price": 100.0, "Risk per share": 0.0},
        ]
    )
    frame = risk_plan_frame(results, risk_budget=1000, capital_limit=10000)
    assert frame["Suggested quantity"].tolist() == [0, 0, 0]
    assert frame["Planned capital"].tolist() == [0.0, 0.0, 0.0]
    assert frame["Planned risk"].tolist() == [0.0, 0.0, 0.0]


def test_missing_entry_column_fails_closed_without_exception():
    results = pd.DataFrame([{"Symbol": "NO_ENTRY", "Risk per share": 2.0}])
    frame = risk_plan_frame(results, risk_budget=1000, capital_limit=10000)
    assert frame.loc[0, "Suggested quantity"] == 0
    assert frame.loc[0, "Planned capital"] == 0
