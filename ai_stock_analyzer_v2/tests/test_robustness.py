import numpy as np
import pandas as pd
import pytest

from algorithmic_trading import robustness as rb


def test_norm_ppf_inverts_cdf_and_known_values():
    for p in (0.001, 0.025, 0.2, 0.5, 0.9, 0.975, 0.999):
        assert rb._norm_cdf(rb._norm_ppf(p)) == pytest.approx(p, abs=1e-7)
    assert rb._norm_ppf(0.975) == pytest.approx(1.959964, abs=1e-5)
    with pytest.raises(ValueError):
        rb._norm_ppf(1.0)


def test_bootstrap_indices_valid_and_block_structure():
    rng = np.random.default_rng(0)
    idx = rb.stationary_bootstrap_indices(5000, 20.0, rng)
    assert idx.min() >= 0 and idx.max() < 5000
    runs = np.mean(np.diff(idx) == 1)  # continuation probability = 1 - 1/20
    assert 0.9 < runs < 0.99
    with pytest.raises(ValueError):
        rb.stationary_bootstrap_indices(10, 0.5, rng)


def test_bootstrap_interval_covers_true_sharpe_and_is_ordered():
    rng = np.random.default_rng(1)
    r = pd.Series(rng.normal(0.0008, 0.01, 1000))
    out = rb.bootstrap_metrics(r, n_boot=300)
    s = out["sharpe"]
    assert s["p5"] < s["median"] < s["p95"]
    assert s["p5"] < r.mean() / r.std() * np.sqrt(252) < s["p95"]
    assert out["max_drawdown"]["p5"] <= out["max_drawdown"]["p95"] <= 0
    assert 0 <= out["prob_loss"] <= 1


def test_bootstrap_is_reproducible_and_validates():
    r = pd.Series(np.random.default_rng(2).normal(0, 0.01, 200))
    assert rb.bootstrap_metrics(r, n_boot=100, seed=5) == rb.bootstrap_metrics(
        r, n_boot=100, seed=5
    )
    with pytest.raises(ValueError):
        rb.bootstrap_metrics(r.iloc[:10])
    with pytest.raises(ValueError):
        rb.bootstrap_metrics(r, n_boot=5)


def test_zero_edge_strategy_has_wide_interval_and_losing_probability():
    r = pd.Series(np.random.default_rng(3).normal(0.0, 0.01, 500))
    out = rb.bootstrap_metrics(r, n_boot=300)
    assert out["sharpe"]["p5"] < 0 < out["sharpe"]["p95"]


def test_probabilistic_sharpe_behaviour():
    rng = np.random.default_rng(4)
    good = pd.Series(rng.normal(0.002, 0.01, 1000))
    none = pd.Series(rng.normal(0.0, 0.01, 1000))
    assert rb.probabilistic_sharpe(good) > 0.99
    assert 0.05 < rb.probabilistic_sharpe(none) < 0.95
    assert rb.probabilistic_sharpe(good, benchmark_sharpe_annual=50) < 0.01
    with pytest.raises(ValueError):
        rb.probabilistic_sharpe(good.iloc[:5])


def test_expected_max_sharpe_grows_with_trials_and_variance():
    assert rb.expected_max_sharpe(1, 0.01) == 0.0
    a, b = rb.expected_max_sharpe(10, 0.01), rb.expected_max_sharpe(1000, 0.01)
    assert 0 < a < b
    assert rb.expected_max_sharpe(10, 0.04) == pytest.approx(2 * a)
    # known value: 100 trials, unit variance -> about 2.5 (Bailey & Lopez de Prado)
    assert rb.expected_max_sharpe(100, 1.0) == pytest.approx(2.5, abs=0.1)


def test_deflation_lowers_confidence_as_more_variants_are_tried():
    rng = np.random.default_rng(6)
    r = pd.Series(rng.normal(0.0006, 0.01, 750))
    best = r.mean() / r.std() * np.sqrt(252)
    few = rb.deflated_sharpe(r, [best, 0.1])
    many = rb.deflated_sharpe(r, [best, *np.random.default_rng(7).normal(0, 0.8, 99)])
    assert many < few
    with pytest.raises(ValueError):
        rb.deflated_sharpe(r, [])


def test_selection_luck_is_flagged_by_the_deflated_sharpe():
    """Best of 100 noise strategies looks great raw but should not pass deflation."""
    rng = np.random.default_rng(8)
    trials = [pd.Series(rng.normal(0, 0.01, 500)) for _ in range(100)]
    sharpes = [t.mean() / t.std() * np.sqrt(252) for t in trials]
    best = trials[int(np.argmax(sharpes))]
    assert rb.probabilistic_sharpe(best) > 0.9  # looks significant on its own
    assert rb.deflated_sharpe(best, sharpes) < 0.95  # but not after 100 tries
