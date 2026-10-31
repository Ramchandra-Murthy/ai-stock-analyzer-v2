import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm

from algorithmic_trading import risk_advanced as ra


def _series(n=1000, seed=1, scale=0.01, df=None):
    rng = np.random.default_rng(seed)
    data = rng.standard_t(df, n) * scale if df else rng.normal(0.0005, scale, n)
    return pd.Series(data, index=pd.bdate_range("2019-01-01", periods=n))


def _frame(n=600, seed=2):
    rng = np.random.default_rng(seed)
    market = rng.normal(0.0004, 0.008, n)[:, None]
    betas = np.array([0.5, 1.0, 1.5])
    data = market * betas + rng.normal(0, 0.004, (n, 3))
    return pd.DataFrame(
        data, columns=["LOW", "MID", "HIGH"], index=pd.bdate_range("2019-01-01", periods=n)
    )


def test_parametric_var_matches_the_normal_formula():
    r = _series()
    expected = -(r.mean() + norm.ppf(0.05) * r.std(ddof=1))
    assert ra.parametric_var(r, 0.95) == pytest.approx(expected)
    assert ra.parametric_var(r, 0.99) > ra.parametric_var(r, 0.95)


def test_cornish_fisher_reduces_to_normal_var_for_symmetric_thin_tails():
    r = _series(n=20000, seed=3)
    assert ra.cornish_fisher_var(r, 0.95) == pytest.approx(ra.parametric_var(r, 0.95), rel=0.05)


def test_cornish_fisher_var_exceeds_normal_var_for_fat_tails_at_99():
    r = _series(n=20000, seed=4, df=3, scale=0.005)
    assert ra.cornish_fisher_var(r, 0.99) > ra.parametric_var(r, 0.99)


def test_var_functions_validate_level_and_sample_size():
    r = _series()
    for fn in (ra.parametric_var, ra.cornish_fisher_var):
        with pytest.raises(ValueError):
            fn(r, 0.4)
        with pytest.raises(ValueError):
            fn(r, 1.0)
    with pytest.raises(ValueError):
        ra.parametric_var(r.iloc[:5])
    with pytest.raises(ValueError):
        ra.cornish_fisher_var(r.iloc[:30])


def test_worst_windows_are_ordered_non_overlapping_and_find_a_planted_crash():
    r = _series(n=300, seed=5, scale=0.004)
    r.iloc[100:105] = -0.04
    worst = ra.worst_windows(r, window=5, count=3)
    assert list(worst) == sorted(worst)
    assert worst.iloc[0] == pytest.approx(0.96**5 - 1)
    assert worst.index[0] == r.index[104]
    positions = [r.index.get_loc(ts) for ts in worst.index]
    assert all(abs(a - b) >= 5 for i, a in enumerate(positions) for b in positions[i + 1 :])


def test_tail_risk_report_is_internally_consistent():
    report = ra.tail_risk_report(_series(df=4, scale=0.006))
    assert report["cvar_95"] >= report["var_95_historical"] > 0
    assert report["cvar_99"] >= report["var_99_historical"]
    assert report["excess_kurtosis"] > 0
    assert report["worst_day"] < 0


def test_monte_carlo_shape_start_value_and_reproducibility():
    r = _series()
    a = ra.monte_carlo_paths(r, horizon=120, n_paths=300, seed=7)
    b = ra.monte_carlo_paths(r, horizon=120, n_paths=300, seed=7)
    c = ra.monte_carlo_paths(r, horizon=120, n_paths=300, seed=8)
    assert a.shape == (300, 121)
    assert (a[:, 0] == 1.0).all()
    assert np.array_equal(a, b) and not np.array_equal(a, c)
    assert (a > 0).all()


def test_monte_carlo_with_non_multiple_horizon_and_block_one():
    r = _series()
    paths = ra.monte_carlo_paths(r, horizon=13, n_paths=50, block=1, seed=1)
    assert paths.shape == (50, 14)
    paths = ra.monte_carlo_paths(r, horizon=13, n_paths=50, block=5, seed=1)
    assert paths.shape == (50, 14)


def test_monte_carlo_median_growth_tracks_the_historical_drift():
    r = _series(n=2000, seed=9)
    paths = ra.monte_carlo_paths(r, horizon=252, n_paths=4000, seed=9)
    expected_log = np.log1p(r).mean() * 252
    assert np.log(np.median(paths[:, -1])) == pytest.approx(expected_log, abs=0.12)


def test_monte_carlo_rejects_bad_arguments():
    r = _series()
    for kwargs in ({"horizon": 0}, {"n_paths": 0}, {"block": 0}):
        with pytest.raises(ValueError):
            ra.monte_carlo_paths(r, **kwargs)
    with pytest.raises(ValueError):
        ra.monte_carlo_paths(r.iloc[:30])


def test_summarise_paths_on_a_hand_built_example():
    paths = np.array([[1.0, 1.1, 1.2], [1.0, 0.7, 0.9], [1.0, 1.0, 1.0], [1.0, 1.3, 1.5]])
    s = ra.summarise_paths(paths, drawdown_limit=0.25)
    assert s["probability_of_loss"] == 0.25
    assert s["probability_drawdown_beyond_limit"] == 0.25
    assert s["worst_max_drawdown"] == pytest.approx(-0.3)
    assert s["terminal_median"] == pytest.approx(1.1)
    assert s["terminal_p5"] <= s["terminal_median"] <= s["terminal_p95"]
    with pytest.raises(ValueError):
        ra.summarise_paths(paths[0])
    with pytest.raises(ValueError):
        ra.summarise_paths(paths, drawdown_limit=1.5)


def test_path_quantiles_are_ordered_and_named():
    paths = ra.monte_carlo_paths(_series(), horizon=60, n_paths=500, seed=3)
    q = ra.path_quantiles(paths)
    assert list(q.columns) == ["p5", "p50", "p95"] and len(q) == 61
    assert (q["p5"] <= q["p50"]).all() and (q["p50"] <= q["p95"]).all()
    with pytest.raises(ValueError):
        ra.path_quantiles(paths, quantiles=(1.5,))


def test_asset_betas_recover_the_planted_ordering_and_average_to_one():
    betas = ra.asset_betas(_frame())
    assert betas["LOW"] < betas["MID"] < betas["HIGH"]
    assert betas.mean() == pytest.approx(1.0)
    with pytest.raises(ValueError):
        ra.asset_betas(_frame()[["LOW"]])


def test_stress_test_scales_with_shock_and_beta():
    r = _frame()
    table = ra.stress_test(r, {"LOW": 0.5, "HIGH": 0.5})
    assert list(table.index) == list(ra.DEFAULT_MARKET_SHOCKS)
    assert (table["portfolio"] < 0).all()
    assert table.loc["Crash (-30%)", "portfolio"] == pytest.approx(
        6 * table.loc["Mild correction (-5%)", "portfolio"]
    )
    assert table.loc["Crash (-30%)", "HIGH"] < table.loc["Crash (-30%)", "LOW"]
    assert (ra.stress_test(r, {"LOW": 1.0}, {"Rally": 0.1})["portfolio"] > 0).all()
    with pytest.raises(ValueError):
        ra.stress_test(r, {"LOW": 1.0}, {})
    with pytest.raises(ValueError):
        ra.stress_test(r, {"NOPE": 1.0})


def test_custom_stress_applies_only_named_shocks():
    assert ra.custom_stress({"A": 0.6, "B": 0.4}, {"A": -0.10}) == pytest.approx(-0.06)
    with pytest.raises(ValueError):
        ra.custom_stress({"A": 1.0}, {"Z": -0.1})


def test_diversification_ratio_is_one_for_a_single_asset_and_above_one_when_mixed():
    r = _frame()
    assert ra.diversification_ratio(r, {"MID": 1.0}) == pytest.approx(1.0)
    assert ra.diversification_ratio(r, {"LOW": 1 / 3, "MID": 1 / 3, "HIGH": 1 / 3}) > 1.0


def test_average_pairwise_correlation_bounds():
    r = _frame()
    assert 0 < ra.average_pairwise_correlation(r) <= 1
    with pytest.raises(ValueError):
        ra.average_pairwise_correlation(r[["LOW"]])


def test_advanced_risk_summary_has_every_key():
    r = _frame()
    summary = ra.advanced_risk_summary(r, {"LOW": 0.2, "MID": 0.3, "HIGH": 0.5})
    assert {"var_95_cornish_fisher", "cvar_99", "max_drawdown", "diversification_ratio"} <= set(
        summary
    )
    assert summary["max_drawdown"] <= 0
