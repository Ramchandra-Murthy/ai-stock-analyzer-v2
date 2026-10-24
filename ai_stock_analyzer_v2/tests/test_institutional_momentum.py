import pandas as pd

from scanner.institutional_momentum import compute_institutional_momentum


def test_institutional_momentum_neutral_without_inputs():
    result = compute_institutional_momentum()
    assert result["score"] == 50.0
    assert result["label"] == "NEUTRAL"


def test_institutional_momentum_combines_positive_inputs():
    flow = pd.DataFrame(
        {
            "Category": ["FII/FPI", "DII"],
            "Date": ["18 Sep 2026", "18 Sep 2026"],
            "Net Value (₹ Cr)": [6000.0, 3000.0],
        }
    )
    board = pd.DataFrame({"Today change %": [1.0, 2.0], "Relative Strength": [1.0, 2.0]})
    sectors = pd.DataFrame(
        {
            "Stocks": [10],
            "Advancers": [8],
            "Decliners": [2],
            "Avg change %": [1.5],
        }
    )
    result = compute_institutional_momentum(flow=flow, board=board, sector_summary=sectors)
    assert result["score"] > 50
    assert result["label"] in {"POSITIVE", "STRONG POSITIVE"}


def test_institutional_momentum_negative_inputs_lower_score():
    flow = pd.DataFrame(
        {
            "Category": ["FII/FPI", "DII"],
            "Date": ["18 Sep 2026", "18 Sep 2026"],
            "Net Value (₹ Cr)": [-6000.0, -3000.0],
        }
    )
    sectors = pd.DataFrame(
        {
            "Stocks": [10],
            "Advancers": [2],
            "Decliners": [8],
            "Avg change %": [-1.5],
        }
    )
    board = pd.DataFrame({"Today change %": [-1.0, -2.0], "Relative Strength": [-1.0, -2.0]})
    result = compute_institutional_momentum(flow=flow, board=board, sector_summary=sectors)
    assert result["score"] < 50
    assert result["label"] in {"NEGATIVE", "STRONG NEGATIVE"}
