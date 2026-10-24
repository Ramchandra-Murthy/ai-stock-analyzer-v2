import pandas as pd
import pytest

from algorithmic_trading.universe_filter import (
    UniverseCriteria,
    candidate_table,
    refine_universe,
)


def test_candidate_table_normalizes_exchange() -> None:
    result = candidate_table(["RELIANCE", "TCS"], "nse")
    assert result["exchange"].tolist() == ["NSE", "NSE"]


def test_refine_by_liquidity_and_price() -> None:
    universe = pd.DataFrame(
        {
            "symbol": ["A", "B", "C"],
            "price": [100, 50, 10],
            "avg_volume": [1_000_000, 100_000, 2_000_000],
            "avg_turnover": [100_000_000, 5_000_000, 20_000_000],
        }
    )
    criteria = UniverseCriteria(
        min_price=20,
        min_avg_volume=500_000,
        min_avg_turnover=10_000_000,
    )
    result = refine_universe(universe, criteria)
    assert result["symbol"].tolist() == ["A"]


def test_optional_beta_and_relative_strength_filters() -> None:
    universe = pd.DataFrame(
        {
            "symbol": ["A", "B", "C"],
            "beta": [0.8, 1.2, 1.8],
            "relative_return_pct": [5.0, 1.0, 8.0],
        }
    )
    criteria = UniverseCriteria(max_beta=1.5, min_relative_return_pct=2.0)
    result = refine_universe(universe, criteria)
    assert result["symbol"].tolist() == ["A"]


def test_missing_symbol_column_fails() -> None:
    with pytest.raises(ValueError, match="symbol"):
        refine_universe(pd.DataFrame({"price": [10]}))
