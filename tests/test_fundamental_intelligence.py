import pandas as pd
import pytest

from ai_trading.fundamental_intelligence import (
    FundamentalSnapshot,
    fundamental_quality_score,
    fundamentals_frame,
    normalize_fundamentals,
)


def test_normalize_fundamentals_and_score() -> None:
    snapshot = normalize_fundamentals(
        {
            "revenue_growth_pct": 20,
            "earnings_growth_pct": 15,
            "profit_margin_pct": 25,
            "debt_to_equity": 0.5,
            "return_on_equity_pct": 18,
            "pe_ratio": 20,
        }
    )
    assert snapshot.revenue_growth_pct == pytest.approx(20.0)
    assert fundamental_quality_score(snapshot) > 50.0


def test_missing_values_are_supported() -> None:
    snapshot = normalize_fundamentals({"pe_ratio": 18})
    assert snapshot.revenue_growth_pct is None
    assert fundamental_quality_score(snapshot) == pytest.approx(84.0)


def test_fundamentals_frame() -> None:
    snapshot = FundamentalSnapshot(10, 8, 12, 0.4, 16, 18)
    frame = fundamentals_frame({"ABC": snapshot})
    assert list(frame.columns)[0] == "symbol"
    assert frame.iloc[0]["symbol"] == "ABC"
    assert frame.iloc[0]["pe_ratio"] == 18
    assert isinstance(frame, pd.DataFrame)
