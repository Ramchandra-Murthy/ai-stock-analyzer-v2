import numpy as np
import pandas as pd
import pytest

from engine.universe_refinement import (
    add_universe_metrics,
    calculate_short_pct_float,
    calculate_value_traded,
    refine_short_universe,
    rolling_beta,
    sector_average_returns,
    universe_refinement_report,
)


def test_value_traded_prefers_ten_day_volume():
    volume = pd.Series([1000, 2000], index=["A", "B"])
    price = pd.Series([100, 100], index=["A", "B"])
    volume_10d = pd.Series([1500, 2500], index=["A", "B"])
    result = calculate_value_traded(volume, price, volume_10d)
    assert result.to_dict() == {"A": 150000.0, "B": 250000.0}


def test_short_pct_float_uses_reported_fallback():
    shares_short = pd.Series([50, np.nan], index=["A", "B"])
    float_shares = pd.Series([100, np.nan], index=["A", "B"])
    reported = pd.Series([0.5, 0.2], index=["A", "B"])
    result = calculate_short_pct_float(shares_short, float_shares, reported)
    assert result.to_dict() == {"A": 0.5, "B": 0.2}


def test_refine_short_universe_applies_liquidity_and_crowding_filters():
    universe = pd.DataFrame(
        {
            "value_traded": [2_000_000, 500_000, 2_000_000, 2_000_000],
            "short_pct_float": [0.20, 0.10, 0.70, 0.20],
            "buyback": [False, False, False, True],
        },
        index=["liquid", "illiquid", "crowded", "buyback"],
    )
    result = refine_short_universe(universe)
    assert list(result.index) == ["liquid"]


def test_fundamental_and_valuation_filters():
    universe = pd.DataFrame(
        {
            "value_traded": [2e6, 2e6, 2e6],
            "short_pct_float": [0.1, 0.1, 0.1],
            "forward_pe": [12, 30, 10],
            "fundamental_deterioration": [True, True, False],
        },
        index=["candidate", "expensive", "healthy"],
    )
    result = refine_short_universe(
        universe,
        max_forward_pe=20,
        require_fundamental_deterioration=True,
    )
    assert list(result.index) == ["candidate"]


def test_rolling_beta_and_sector_average_returns():
    stock = pd.Series([0.01, 0.02, -0.01, 0.03, 0.02, 0.01])
    market = pd.Series([0.01, 0.01, -0.005, 0.015, 0.01, 0.005])
    beta = rolling_beta(stock, market, window=3)
    assert beta.iloc[:2].isna().all()
    assert np.isfinite(beta.iloc[-1])

    returns = pd.DataFrame(
        {
            "A": [0.01, 0.03],
            "B": [0.03, 0.01],
            "C": [-0.02, 0.00],
        }
    )
    sectors = pd.Series({"A": "Tech", "B": "Tech", "C": "Energy"})
    result = sector_average_returns(returns, sectors)
    assert result["Tech"] == pytest.approx(0.02)
    assert result["Energy"] == pytest.approx(-0.01)


def test_add_metrics_and_report():
    universe = pd.DataFrame(index=["A", "B"])
    volume = pd.Series([20000, 5000], index=["A", "B"])
    price = pd.Series([100, 100], index=["A", "B"])
    result = add_universe_metrics(universe, volume, price)
    assert result["value_traded"].tolist() == [2_000_000.0, 500_000.0]

    report = universe_refinement_report(
        result,
        min_value_traded=1_000_000,
    )
    assert report == {"input_count": 2, "output_count": 1, "removed_count": 1}


def test_invalid_filters_raise():
    universe = pd.DataFrame({"value_traded": [2e6]})
    with pytest.raises(ValueError):
        refine_short_universe(universe, min_value_traded=0)
    with pytest.raises(ValueError):
        refine_short_universe(universe, max_short_pct_float=1.5)
    with pytest.raises(ValueError):
        refine_short_universe(universe, max_beta=0)
