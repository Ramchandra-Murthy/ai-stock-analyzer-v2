import numpy as np
import pandas as pd
import pytest

from algorithmic_trading import volatility_forecast as vf


def _garch_sim(n=6000, omega=2e-6, alpha=0.08, beta=0.90, seed=0):
    rng = np.random.default_rng(seed)
    h = omega / (1 - alpha - beta)
    r = np.empty(n)
    for t in range(n):
        r[t] = np.sqrt(h) * rng.standard_normal()
        h = omega + alpha * r[t] ** 2 + beta * h
    return pd.Series(r, index=pd.bdate_range("2000-01-03", periods=n))


def test_ewma_hand_computed():
    r = pd.Series(
        np.r_[np.full(20, 0.01), 0.02, 0.0], index=pd.bdate_range("2024-01-01", periods=22)
    )
    # pad to 30 rows so the guard passes
    r = pd.concat([r, pd.Series(0.0, index=pd.bdate_range("2024-02-01", periods=8))])
    v = vf.ewma_variance(r, 0.9)
    seed = 0.0  # variance of 20 identical returns
    expected = seed
    for x in r.iloc[:21]:
        expected = 0.9 * expected + 0.1 * x**2
    assert v.iloc[20] == pytest.approx(expected)


def test_ewma_forecast_at_t_ignores_the_future():
    r = _garch_sim(400)
    full = vf.ewma_variance(r)
    pd.testing.assert_series_equal(full.iloc[:300], vf.ewma_variance(r.iloc[:300]))
    with pytest.raises(ValueError):
        vf.ewma_variance(r, 1.0)
    with pytest.raises(ValueError):
        vf.ewma_variance(r.iloc[:10])


def test_garch_recovers_known_parameters():
    fit = vf.fit_garch(_garch_sim(8000, seed=1))
    assert fit.alpha == pytest.approx(0.08, abs=0.03)
    assert fit.beta == pytest.approx(0.90, abs=0.04)
    assert fit.persistence == pytest.approx(0.98, abs=0.015)
    assert fit.long_run_variance == pytest.approx(2e-6 / 0.02, rel=0.35)
    assert fit.half_life > 15


def test_garch_on_constant_variance_noise_has_low_alpha():
    r = pd.Series(np.random.default_rng(3).normal(0, 0.01, 3000))
    fit = vf.fit_garch(r)
    assert fit.alpha < 0.08 or fit.persistence < 0.9


def test_garch_input_validation():
    with pytest.raises(ValueError):
        vf.fit_garch(pd.Series(np.zeros(100)))


def test_garch_forecast_series_is_causal_and_term_structure_decays_to_long_run():
    r = _garch_sim(3000, seed=4)
    fit = vf.fit_garch(r.iloc[:2000])
    full = vf.garch_forecast_series(r.iloc[:2500], fit)
    # forecast at t must not depend on returns after t
    cut = vf.garch_forecast_series(r.iloc[:2400], fit)
    assert np.array_equal(full.iloc[:2400].to_numpy(), cut.to_numpy())
    ts = vf.garch_term_structure(fit, fit.long_run_variance * 3, 2000)
    assert ts[0] == pytest.approx(fit.long_run_variance * 3)
    assert (
        np.all(np.diff(ts) <= 0)
        and ts[1] < ts[0]
        and ts[-1] == pytest.approx(fit.long_run_variance, rel=1e-2)
    )
    low = vf.garch_term_structure(fit, fit.long_run_variance / 3, 50)
    assert np.all(np.diff(low) >= 0) and low[1] > low[0]


def test_qlike_prefers_the_true_variance():
    rng = np.random.default_rng(0)
    y = pd.Series(rng.normal(0, 0.01, 5000) ** 2)
    good = pd.Series(1e-4, index=y.index)
    assert vf.qlike(good, y) < vf.qlike(good * 3, y)
    assert vf.qlike(good, y) < vf.qlike(good / 3, y)


def test_compare_forecasters_prefers_conditional_models_on_garch_data_and_validates():
    table = vf.compare_forecasters(_garch_sim(1800, seed=5), refit_every=250, min_train=900)
    assert set(table.index) == {"Rolling 20d", "EWMA 0.94", "GARCH(1,1)"}
    assert table.index[-1] == "Rolling 20d" or table.index[0] in ("GARCH(1,1)", "EWMA 0.94")
    with pytest.raises(ValueError):
        vf.compare_forecasters(_garch_sim(300))


def test_annualised_volatility():
    assert vf.annualised_volatility(0.0001) == pytest.approx(0.01 * np.sqrt(252))
    assert vf.annualised_volatility(-1) == 0.0
