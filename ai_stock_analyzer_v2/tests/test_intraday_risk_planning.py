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
