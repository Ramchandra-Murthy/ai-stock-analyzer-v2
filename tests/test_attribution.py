import numpy as np
import pandas as pd
import pytest

from algorithmic_trading.attribution import (
    factor_regression,
    return_contributions,
    rolling_max_drawdown,
    rolling_sharpe,
)

IDX = pd.bdate_range("2022-01-01", periods=400)


def _factors(seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({"mkt": rng.normal(4e-4, 0.01, 400), "mom": rng.normal(0, 0.006, 400)}, IDX)


def test_regression_recovers_known_beta_and_alpha():
    f = _factors()
    noise = np.random.default_rng(1).normal(0, 0.001, 400)
    r = 0.0002 + 1.2 * f["mkt"] + 0.4 * f["mom"] + noise
    fit = factor_regression(r, f)
    assert fit.betas["mkt"] == pytest.approx(1.2, abs=0.05)
    assert fit.betas["mom"] == pytest.approx(0.4, abs=0.1)
    assert fit.alpha_annual == pytest.approx(0.0002 * 252, abs=0.03)
    assert fit.r_squared > 0.95 and fit.observations == 400


def test_pure_noise_has_no_significant_alpha():
    f = _factors()
    r = pd.Series(np.random.default_rng(5).normal(0, 0.01, 400), IDX)
    assert abs(factor_regression(r, f).alpha_t) < 3


def test_timezone_aware_factor_still_aligns():
    f = _factors()[["mkt"]]
    f.index = f.index.tz_localize("Asia/Kolkata")
    r = 1.0 * _factors()["mkt"] + 0.0001
    assert factor_regression(r, f).observations == 400


def test_regression_rejects_short_history_and_collinear_factors():
    f = _factors()
    with pytest.raises(ValueError, match="overlapping"):
        factor_regression(f["mkt"].iloc[:20], f)
    f2 = f.assign(dup=f["mkt"])
    with pytest.raises(ValueError, match="collinear"):
        factor_regression(f["mkt"] * 1.1, f2)


def test_rolling_sharpe_and_drawdown_shapes():
    r = _factors()["mkt"]
    s = rolling_sharpe(r, 63)
    assert s.iloc[:62].isna().all() and s.iloc[62:].notna().all()
    dd = rolling_max_drawdown(r, 126)
    assert (dd.dropna() <= 0).all()
    with pytest.raises(ValueError):
        rolling_sharpe(r, 5)


def test_contributions_add_up_to_weighted_total():
    rets = pd.DataFrame({"A": [0.01] * 30, "B": [-0.02] * 30})
    c = return_contributions(rets, {"A": 3, "B": 1})
    assert c["A"] == pytest.approx(0.75 * 0.01 * 30)
    assert c["B"] == pytest.approx(0.25 * -0.02 * 30)
    with pytest.raises(ValueError):
        return_contributions(rets, {"Z": 1})
