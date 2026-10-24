import numpy as np
import pandas as pd
import pytest

from algorithmic_trading.asset_allocation import (
    allocation_summary,
    apply_weight_cap,
    calculate_portfolio_return,
    calculate_raw_weight,
    clip_weight,
    equal_weight,
    exposure_allocation,
    inverse_volatility_weight,
    minimum_variance_weight,
    risk_appetite,
    temporary_boost,
    upper_band_limit,
)


@pytest.fixture
def returns() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "RELIANCE": [0.01, -0.005, 0.008, 0.004],
            "TCS": [0.005, 0.002, -0.003, 0.004],
            "INFY": [0.003, 0.001, 0.002, -0.001],
        }
    )


def test_equal_weight(returns: pd.DataFrame) -> None:
    weights = equal_weight(returns)
    assert weights.sum() == pytest.approx(1.0)
    assert np.allclose(weights.to_numpy(), 1 / 3)


def test_inverse_volatility_weight(returns: pd.DataFrame) -> None:
    weights = inverse_volatility_weight(returns)
    assert weights.sum() == pytest.approx(1.0)
    assert (weights >= 0).all()


def test_minimum_variance_weight(returns: pd.DataFrame) -> None:
    weights = minimum_variance_weight(returns)
    assert weights.sum() == pytest.approx(1.0)
    assert (weights >= 0).all()


def test_weight_cap(returns: pd.DataFrame) -> None:
    weights = equal_weight(returns)
    capped = apply_weight_cap(weights, 0.40)
    assert capped.max() <= 0.40 + 1e-12
    assert capped.sum() == pytest.approx(1.0)


def test_allocation_summary(returns: pd.DataFrame) -> None:
    summary = allocation_summary(equal_weight(returns))
    assert list(summary.columns) == ["weight", "weight_pct"]


def test_upper_band_limit_matches_chapter_formula():
    assert upper_band_limit(
        st_dd=0.20,
        lt_dd=0.40,
        corr_adj=0.10,
        lt_dd_tolerance=0.30,
        st_dd_tolerance=0.10,
        lqdty_haircut=0.05,
    ) == pytest.approx(0.43)


def test_risk_appetite_stays_within_bounds():
    equity = pd.Series([100, 98, 95, 100], dtype=float)
    result = risk_appetite(
        equity,
        max_drawdown_tolerance=-0.10,
        min_risk=0.5,
        max_risk=1.0,
        smoothing_span=2,
    )
    assert result.between(0.5, 1.0).all()
    assert result.iloc[-1] > result.iloc[2]


def test_temporary_boost_only_when_other_strategy_fails():
    series1 = pd.Series([100.0, 90.0, 80.0, 80.0])
    series2 = pd.Series([100.0, 100.0, 110.0, 120.0])
    boost = temporary_boost(series1, series2, boost_val=2.0, duration=1)
    assert boost.tolist() == [1.0, 2.0, 2.0, 1.0]


def test_weight_helpers():
    raw = calculate_raw_weight(0.30, 2.0, 1.5)
    assert raw == pytest.approx(0.9)
    assert clip_weight(raw, 0.30, 0.5, 1.0) == pytest.approx(0.3)


def test_portfolio_return():
    assert calculate_portfolio_return(0.3, 0.7, 0.02, -0.01) == pytest.approx(-0.001)


def test_exposure_allocation_is_recursive_and_no_lookahead():
    index = pd.date_range("2026-01-01", periods=5, freq="D")
    mr = pd.Series([0.01, 0.01, -0.20, 0.01, 0.01], index=index)
    tf = pd.Series([-0.01, 0.01, 0.01, 0.01, -0.01], index=index)

    result = exposure_allocation(
        mr,
        tf,
        initial_capital=100.0,
        upper_band_mr=0.30,
        upper_band_tf=0.86,
        min_exposure=0.5,
        max_exposure=1.0,
        k=1,
        risk_params={
            "max_drawdown_tolerance": -0.10,
            "min_risk": 0.5,
            "max_risk": 1.0,
            "smoothing_span": 2,
        },
    )

    assert list(result.columns) == [
        "equity",
        "w_MR",
        "w_TF",
        "portfolio_returns",
        "gross_exposure",
        "mr_boost",
        "tf_boost",
    ]
    assert result.iloc[0]["equity"] == pytest.approx(100.0)
    assert np.isnan(result.iloc[0]["w_MR"])
    assert np.isnan(result.iloc[0]["w_TF"])
    assert result["equity"].iloc[1:].notna().all()
    assert result["gross_exposure"].iloc[1:].between(0.5, 1.0).all()


def test_exposure_allocation_rejects_mismatched_inputs():
    with pytest.raises(ValueError):
        exposure_allocation(
            pd.Series([0.01, 0.02]),
            pd.Series([0.01]),
            100.0,
            0.3,
            0.86,
            0.5,
            1.0,
            1,
            {
                "max_drawdown_tolerance": -0.10,
                "min_risk": 0.5,
                "max_risk": 1.0,
            },
        )

    with pytest.raises(ValueError):
        upper_band_limit(0.0, 0.4, 0.1, 0.3, 0.1, 0.05)


def test_weight_cap_leaves_cash_when_full_investment_would_break_cap() -> None:
    weights = pd.Series([0.25, 0.25, 0.25, 0.25], index=list("ABCD"))
    capped = apply_weight_cap(weights, 0.20)

    assert capped.max() == pytest.approx(0.20)
    assert capped.sum() == pytest.approx(0.80)


def test_weight_cap_redistributes_when_full_investment_is_feasible() -> None:
    weights = pd.Series([0.80, 0.10, 0.10], index=list("ABC"))
    capped = apply_weight_cap(weights, 0.50)

    assert capped.max() <= 0.50 + 1e-12
    assert capped.sum() == pytest.approx(1.0)
    assert capped.tolist() == pytest.approx([0.50, 0.25, 0.25])
