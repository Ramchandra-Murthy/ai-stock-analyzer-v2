import numpy as np
import pandas as pd
import pytest

from algorithmic_trading import pairs_trading as pt


def _ou_pair(n=800, seed=1, theta=0.08, beta=0.8):
    rng = np.random.default_rng(seed)
    lx = np.cumsum(rng.normal(0.0003, 0.012, n)) + 4.0
    s = np.zeros(n)
    for t in range(1, n):
        s[t] = (1 - theta) * s[t - 1] + rng.normal(0, 0.01)
    ly = 0.3 + beta * lx + s
    idx = pd.bdate_range("2018-01-01", periods=n)
    return pd.Series(np.exp(ly), idx), pd.Series(np.exp(lx), idx), s


def test_half_life_recovers_ou_parameter():
    rng = np.random.default_rng(0)
    s = np.zeros(20000)
    for t in range(1, len(s)):
        s[t] = 0.9 * s[t - 1] + rng.normal()
    assert pt.half_life(s) == pytest.approx(np.log(2) / -np.log(0.9), rel=0.1)


def test_random_walk_has_no_half_life_or_is_long():
    rng = np.random.default_rng(3)
    hl = pt.half_life(np.cumsum(rng.normal(size=2000)))
    assert hl is None or hl > 50


def test_false_positive_rate_on_independent_random_walks_is_near_nominal():
    rng = np.random.default_rng(42)
    hits, trials = 0, 600
    for _ in range(trials):
        y = pd.Series(np.cumsum(rng.normal(size=300)))
        x = pd.Series(np.cumsum(rng.normal(size=300)))
        hits += pt.engle_granger(y, x).cointegrated_5pct
    assert 0.02 <= hits / trials <= 0.09  # nominal 5%; finite-sample distortion allowed


def test_power_on_a_truly_cointegrated_pair():
    y, x, _ = _ou_pair(600)
    r = pt.engle_granger(np.log(y), np.log(x))
    assert r.cointegrated_5pct and r.beta == pytest.approx(0.8, abs=0.1)
    assert r.half_life is not None and 3 < r.half_life < 20


def test_input_validation():
    with pytest.raises(ValueError):
        pt.engle_granger(pd.Series(range(10)), pd.Series(range(10)))
    with pytest.raises(ValueError):
        pt.pair_signals(pd.Series([0.0]), entry=1, exit_=2)


def test_signals_state_machine():
    z = pd.Series([0, -2.5, -1.0, -0.2, 0.0, 2.2, 1.0, 0.3, 2.5, 4.5, 0.0])
    assert pt.pair_signals(z).tolist() == [0, 1, 1, 0, 0, -1, -1, 0, -1, 0, 0]


def test_zscore_is_causal():
    s = pd.Series(np.random.default_rng(0).normal(size=300)).cumsum()
    full = pt.spread_zscore(s, 30)
    pd.testing.assert_series_equal(full.iloc[:200], pt.spread_zscore(s.iloc[:200], 30))


def test_backtest_runs_oos_only_and_profits_on_mean_reverting_pair():
    y, x, _ = _ou_pair(900)
    res = pt.backtest_pair(y, x, cost_bps=0.0)
    assert res.formation.cointegrated_5pct
    cut = int(900 * 0.5)
    assert (res.position.iloc[:cut] == 0).all()
    assert res.returns.index[0] == y.index[cut]
    assert res.trades > 3 and res.metrics["total_return"] > 0


def test_costs_reduce_result_and_frozen_hedge_ratio_uses_formation_only():
    y, x, _ = _ou_pair(900)
    free = pt.backtest_pair(y, x, cost_bps=0.0)
    costly = pt.backtest_pair(y, x, cost_bps=30.0)
    assert costly.metrics["total_return"] < free.metrics["total_return"]
    altered = y.copy()
    altered.iloc[600:] *= 1.5  # shock after the formation window
    assert pt.backtest_pair(altered, x).formation.beta == pytest.approx(free.formation.beta)


def test_no_lookahead_returns_before_a_cut_unchanged():
    y, x, _ = _ou_pair(900)
    base = pt.backtest_pair(y, x)
    altered = y.copy()
    altered.iloc[700:] *= np.linspace(1, 2, 200)
    changed = pt.backtest_pair(altered, x)
    t = y.index[700]
    pd.testing.assert_series_equal(
        base.returns[base.returns.index < t], changed.returns[changed.returns.index < t]
    )


def test_backtest_validation_and_scan():
    y, x, _ = _ou_pair(900)
    with pytest.raises(ValueError):
        pt.backtest_pair(y.iloc[:50], x.iloc[:50])
    with pytest.raises(ValueError):
        pt.backtest_pair(y, x, formation_fraction=0.99)
    table = pt.scan_pairs(pd.DataFrame({"A": y, "B": x}), [("A", "B"), ("A", "Z")])
    assert len(table) == 1 and bool(table["5% cointegrated"].iloc[0])
