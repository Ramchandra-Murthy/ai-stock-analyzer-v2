import numpy as np
import pandas as pd
import pytest

from algorithmic_trading import portfolio_optimizer as po
from algorithmic_trading import risk_sizing as ps


def _rets(n=700, seed=0):
    rng = np.random.default_rng(seed)
    vols = np.array([0.006, 0.010, 0.015, 0.02])
    common = rng.normal(0, 0.006, n)[:, None]
    data = rng.normal(0.0004, 1, (n, 4)) * vols + 0.5 * common
    return pd.DataFrame(data, columns=list("ABCD"), index=pd.bdate_range("2020-01-01", periods=n))


def _valid(w, cap=1.0):
    assert w.sum() == pytest.approx(1.0) and (w >= -1e-9).all() and (w <= cap + 1e-9).all()


@pytest.mark.parametrize("method", po.METHODS)
def test_every_method_gives_valid_long_only_weights(method):
    _valid(po.optimise(_rets(), method))


def test_min_variance_beats_equal_weight_in_sample_and_favours_low_vol():
    r = _rets()
    mv = po.optimise(r, "Minimum variance")
    eq = po.optimise(r, "Equal weight")
    assert (
        po.portfolio_stats(mv, r)["annual_volatility"]
        < po.portfolio_stats(eq, r)["annual_volatility"]
    )
    assert mv["A"] == mv.max()


def test_min_variance_two_uncorrelated_assets_matches_closed_form():
    cov = pd.DataFrame(np.diag([0.04, 0.01]), index=["X", "Y"], columns=["X", "Y"])
    w = po.min_variance(cov)
    assert w["X"] == pytest.approx(0.2, abs=1e-4)  # w_x = var_y / (var_x + var_y)


def test_risk_parity_equalises_contributions():
    r = _rets()
    cov = po.covariance(r)
    w = po.risk_parity(cov)
    rc = w * (cov @ w)
    assert (rc.max() - rc.min()) / rc.mean() < 0.02


def test_risk_parity_uncorrelated_is_inverse_vol():
    cov = pd.DataFrame(np.diag([0.04, 0.01]), index=["X", "Y"], columns=["X", "Y"])
    assert po.risk_parity(cov)["X"] == pytest.approx(1 / 3, abs=1e-3)


def test_hrp_gives_calmer_assets_more_weight_and_is_valid():
    w = po.optimise(_rets(), "Hierarchical risk parity")
    _valid(w)
    assert w["A"] > w["D"]


def test_weight_cap_is_respected_and_validated():
    w = po.optimise(_rets(), "Minimum variance", max_weight=0.4)
    _valid(w, 0.4)
    with pytest.raises(ValueError):
        po.optimise(_rets(), "Minimum variance", max_weight=0.2)  # 4 assets cannot sum to 1


def test_max_sharpe_prefers_the_high_return_asset():
    r = _rets()
    r["B"] += 0.002
    assert po.optimise(r, "Maximum Sharpe")["B"] == po.optimise(r, "Maximum Sharpe").max()


def test_max_sharpe_errors_when_nothing_has_positive_return():
    r = _rets() - 0.01
    with pytest.raises(ValueError):
        po.optimise(r, "Maximum Sharpe")


def test_validation():
    with pytest.raises(ValueError):
        po.optimise(_rets(), "Magic")
    with pytest.raises(ValueError):
        po.covariance(_rets().iloc[:20])


def test_walk_forward_weights_only_use_past_data():
    r = _rets(900)
    base = po.walk_forward_weights(r, "Minimum variance", train=300, rebalance=63)
    altered = r.copy()
    altered.iloc[600:] *= 5.0
    changed = po.walk_forward_weights(altered, "Minimum variance", train=300, rebalance=63)
    # blocks that start before 600 only use data before 600 to choose weights
    first = base.index[base.index < r.index[600]]
    ok = first[first < r.index[600 - 1]]
    pd.testing.assert_series_equal(base.loc[ok], changed.loc[ok])
    with pytest.raises(ValueError):
        po.walk_forward_weights(r.iloc[:200], "Minimum variance")


def test_kelly_hand_values():
    assert ps.kelly_fraction(0.6, 1.0) == pytest.approx(0.2)
    assert ps.kelly_fraction(0.4, 1.0) == 0.0
    assert ps.kelly_fraction(0.5, 2.0) == pytest.approx(0.25)
    assert ps.fractional_kelly(0.6, 1.0, 0.5) == pytest.approx(0.1)
    assert ps.fractional_kelly(0.9, 5.0, 1.0, cap=0.25) == 0.25
    for bad in ((0, 1), (1, 1), (0.5, 0)):
        with pytest.raises(ValueError):
            ps.kelly_fraction(*bad)


def test_risk_based_quantity():
    r = ps.risk_based_quantity(1_000_000, 0.01, entry=2_500, stop=2_450)
    assert r["quantity"] == 200 and r["risk_amount"] == pytest.approx(10_000)
    lots = ps.risk_based_quantity(5_000_000, 0.002, entry=25_000, stop=24_900, lot_size=65)
    assert (
        lots["lots"] == 1
        and lots["quantity"] == 65
        and lots["risk_pct_of_capital"] <= 0.002
        and lots["limited_by"] == 0.0
    )
    capped = ps.risk_based_quantity(100_000, 0.02, entry=100, stop=99.5, max_position_pct=0.2)
    assert capped["notional"] <= 20_000 and capped["limited_by"] == 1.0
    for kw in ({"entry": 100, "stop": 100}, {"entry": -1, "stop": 1}):
        with pytest.raises(ValueError):
            ps.risk_based_quantity(1e5, 0.01, **kw)


def test_atr_stop():
    assert ps.atr_stop(100, 2, 2) == 96
    assert ps.atr_stop(100, 2, 2, long=False) == 104
    with pytest.raises(ValueError):
        ps.atr_stop(10, 6, 2)
