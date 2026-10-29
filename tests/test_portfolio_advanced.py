import numpy as np
import pandas as pd
import pytest

from algorithmic_trading import portfolio_advanced as pa
from algorithmic_trading import portfolio_optimizer as po


def _rets(n=700, seed=0):
    rng = np.random.default_rng(seed)
    vols = np.array([0.006, 0.010, 0.015, 0.02])
    common = rng.normal(0, 0.006, n)[:, None]
    data = rng.normal(0.0004, 1, (n, 4)) * vols + 0.5 * common
    return pd.DataFrame(data, columns=list("ABCD"), index=pd.bdate_range("2020-01-01", periods=n))


def _inputs():
    r = _rets()
    cov = po.covariance(r)
    mean = r.mean() * po.TRADING_DAYS
    return mean, cov


def test_frontier_volatility_and_return_rise_together():
    mean, cov = _inputs()
    points, weights = pa.efficient_frontier(mean, cov, n_points=15)
    assert len(points) == len(weights) >= 10
    assert points["return"].is_monotonic_increasing
    assert points["volatility"].iloc[0] == points["volatility"].min()
    assert points["volatility"].iloc[-1] > points["volatility"].iloc[0]


def test_frontier_first_point_is_the_minimum_variance_portfolio():
    mean, cov = _inputs()
    points, weights = pa.efficient_frontier(mean, cov, n_points=10)
    mv = po.min_variance(cov)
    assert weights.iloc[0].to_numpy() == pytest.approx(mv.to_numpy(), abs=1e-3)
    assert points["volatility"].iloc[0] == pytest.approx(
        float(np.sqrt(mv.to_numpy() @ cov.to_numpy() @ mv.to_numpy())), rel=1e-3
    )


def test_frontier_weights_are_long_only_sum_to_one_and_respect_cap():
    mean, cov = _inputs()
    _, weights = pa.efficient_frontier(mean, cov, n_points=12, max_weight=0.5)
    assert (weights >= -1e-9).all().all() and (weights <= 0.5 + 1e-9).all().all()
    assert weights.sum(axis=1).to_numpy() == pytest.approx(1.0)


def test_frontier_end_point_is_the_highest_returning_asset_when_uncapped():
    mean, cov = _inputs()
    points, _ = pa.efficient_frontier(mean, cov, n_points=8)
    assert points["return"].iloc[-1] == pytest.approx(mean.max(), rel=1e-3)


def test_frontier_rejects_bad_inputs():
    mean, cov = _inputs()
    with pytest.raises(ValueError):
        pa.efficient_frontier(mean, cov, n_points=2)
    with pytest.raises(ValueError):
        pa.efficient_frontier(mean, cov, max_weight=0.1)  # cannot sum to 1 over 4 assets
    with pytest.raises(ValueError):
        pa.efficient_frontier(pd.Series(0.1, index=cov.index), cov)  # identical returns


def test_implied_returns_match_the_formula():
    _, cov = _inputs()
    w = pd.Series([0.4, 0.3, 0.2, 0.1], index=cov.index)
    pi = pa.implied_returns(cov, w, risk_aversion=3.0)
    assert pi.to_numpy() == pytest.approx(3.0 * cov.to_numpy() @ w.to_numpy())
    assert (pi > 0).all()


def test_implied_returns_validate_weights():
    _, cov = _inputs()
    with pytest.raises(ValueError):
        pa.implied_returns(cov, {"A": 1.0})  # missing assets
    with pytest.raises(ValueError):
        pa.implied_returns(cov, dict.fromkeys("ABCD", -0.25))
    with pytest.raises(ValueError):
        pa.implied_returns(cov, dict.fromkeys("ABCD", 0.25), risk_aversion=0)


def test_no_views_returns_the_market_implied_prior():
    _, cov = _inputs()
    w = dict.fromkeys("ABCD", 0.25)
    assert pa.black_litterman_returns(cov, w, []).to_numpy() == pytest.approx(
        pa.implied_returns(cov, w).to_numpy()
    )


def test_bullish_view_raises_that_assets_posterior_and_more_so_with_confidence():
    _, cov = _inputs()
    w = dict.fromkeys("ABCD", 0.25)
    prior = pa.implied_returns(cov, w)["B"]
    low = pa.black_litterman_returns(cov, w, [pa.View({"B": 1.0}, prior + 0.10, 0.2)])["B"]
    high = pa.black_litterman_returns(cov, w, [pa.View({"B": 1.0}, prior + 0.10, 0.9)])["B"]
    assert prior < low < high < prior + 0.10 + 1e-9


def test_near_certain_absolute_view_lands_close_to_the_view():
    _, cov = _inputs()
    w = dict.fromkeys("ABCD", 0.25)
    posterior = pa.black_litterman_returns(
        cov, w, [pa.View({"C": 1.0}, 0.30, 0.999)], tau=0.5
    )
    assert posterior["C"] == pytest.approx(0.30, abs=0.01)


def test_relative_view_widens_the_gap_between_the_two_assets():
    _, cov = _inputs()
    w = dict.fromkeys("ABCD", 0.25)
    prior = pa.implied_returns(cov, w)
    view = pa.View({"A": 1.0, "D": -1.0}, (prior["A"] - prior["D"]) + 0.05, 0.7)
    post = pa.black_litterman_returns(cov, w, [view])
    assert post["A"] - post["D"] > prior["A"] - prior["D"]


def test_view_validation():
    _, cov = _inputs()
    w = dict.fromkeys("ABCD", 0.25)
    for bad in (
        pa.View({"A": 1.0}, 0.1, 0.0),
        pa.View({"A": 1.0}, 0.1, 1.0),
        pa.View({}, 0.1, 0.5),
        pa.View({"ZZZ": 1.0}, 0.1, 0.5),
    ):
        with pytest.raises(ValueError):
            pa.black_litterman_returns(cov, w, [bad])
    with pytest.raises(ValueError):
        pa.black_litterman_returns(cov, w, [pa.View({"A": 1.0}, 0.1, 0.5)], tau=0)


def test_portfolio_weights_are_valid_and_tilt_toward_the_viewed_asset():
    _, cov = _inputs()
    w = dict.fromkeys("ABCD", 0.25)
    base = pa.black_litterman_portfolio(cov, w, [])["weights"]
    view = pa.View({"C": 1.0}, pa.implied_returns(cov, w)["C"] + 0.15, 0.8)
    tilted = pa.black_litterman_portfolio(cov, w, [view], max_weight=0.6)
    assert tilted["weights"].sum() == pytest.approx(1.0)
    assert (tilted["weights"] >= -1e-9).all() and (tilted["weights"] <= 0.6 + 1e-9).all()
    assert tilted["weights"]["C"] > base["C"]
    assert set(tilted) == {"prior", "posterior", "weights"}
