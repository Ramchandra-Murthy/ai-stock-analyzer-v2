"""Tests for the momentum portfolio backtester."""

import numpy as np
import pandas as pd
import pytest

from algorithmic_trading import momentum_portfolio as mp
from algorithmic_trading.trading_costs import india_cost_model


def _prices(n: int = 600, m: int = 6, seed: int = 11) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    drift = np.linspace(-0.0004, 0.0012, m)
    rets = rng.normal(drift, 0.013, size=(n, m))
    idx = pd.bdate_range("2020-01-01", periods=n)
    return pd.DataFrame(
        100 * np.exp(np.cumsum(rets, axis=0)), index=idx, columns=list("ABCDEF")[:m]
    )


def _reference(prices, target_fn, first, every, cost_rate):
    """Independent dollar-based simulation: track holdings in currency, trade at the close."""
    n = len(prices)
    px = prices.ffill()
    value = 1.0
    cash = 1.0
    units = pd.Series(0.0, index=prices.columns)
    out = {}
    pending = None
    for t in range(n):
        before = value
        if pending is not None:
            target_value = pending * value
            current_value = units * px.iloc[t - 1]  # trade at the previous close
            traded = (target_value - current_value).abs().sum()
            fee = traded * cost_rate
            units = target_value / px.iloc[t - 1]
            cash = value - target_value.sum()
            value -= fee
            cash -= fee
            pending = None
        if t > 0:
            value = float((units * px.iloc[t]).sum() + cash)
        out[prices.index[t]] = value / before - 1.0 if t > 0 else 0.0
        if t >= first and (t - first) % every == 0 and t < n - 1:
            pending = target_fn(prices.iloc[: t + 1]).reindex(prices.columns).fillna(0.0)
    return pd.Series(out)


def test_buy_and_hold_after_one_rebalance_matches_weighted_asset_growth() -> None:
    prices = _prices(300, 3)
    target = mp.momentum_target(top_n=2, lookback=100, skip=10)
    result = mp.simulate_portfolio(
        prices, target, first_rebalance=100, rebalance_every=10_000, cost_bps=0.0
    )

    weights = target(prices.iloc[:101])
    growth = prices.iloc[-1] / prices.iloc[101]  # bought at close of bar 100, earns from 101
    growth = prices.iloc[-1] / prices.iloc[100]
    expected = float((weights * growth).sum() + (1 - weights.sum())) - 1.0
    assert result.equity.iloc[-1] - 1.0 == pytest.approx(expected, rel=1e-9)


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_engine_matches_independent_dollar_reference_with_costs(seed: int) -> None:
    prices = _prices(400, 5, seed)
    target = mp.momentum_target(top_n=3, lookback=120, skip=10)
    result = mp.simulate_portfolio(
        prices, target, first_rebalance=120, rebalance_every=21, cost_bps=10.0
    )

    ref = _reference(prices, target, 120, 21, 10.0 / 10_000.0)
    pd.testing.assert_series_equal(
        result.returns,
        ref.loc[result.returns.index],
        check_names=False,
        check_freq=False,
        atol=1e-10,
        rtol=0,
    )


def test_no_lookahead_returns_before_a_cut_ignore_later_prices() -> None:
    prices = _prices(500, 5)
    cut = 352  # the rebalance at bar 351 (120 + 11 * 21) decides the weights held at the cut
    base, _ = mp.run_momentum_portfolio(prices, top_n=2, lookback=120)
    altered = prices.copy()
    altered.iloc[cut:] = altered.iloc[cut:] * np.linspace(1, 4, len(prices) - cut)[:, None]
    changed, _ = mp.run_momentum_portfolio(altered, top_n=2, lookback=120)

    t = prices.index[cut]
    pd.testing.assert_series_equal(
        base.returns[base.returns.index < t], changed.returns[changed.returns.index < t]
    )
    # weights held *on* the cut bar were chosen at bar 351's close, before any altered price
    pd.testing.assert_frame_equal(base.weights.loc[:t], changed.weights.loc[:t])
    assert not base.weights.equals(changed.weights)  # but later decisions do react to new data


def test_first_day_turnover_is_full_investment_and_costs_reduce_returns() -> None:
    prices = _prices(400, 5)
    free, _ = mp.run_momentum_portfolio(prices, top_n=3, lookback=120, cost_bps=0.0)
    costly, _ = mp.run_momentum_portfolio(prices, top_n=3, lookback=120, cost_bps=25.0)
    nse, _ = mp.run_momentum_portfolio(
        prices, top_n=3, lookback=120, cost_model=india_cost_model("delivery", slippage_bps=10)
    )

    assert free.turnover.iloc[0] == pytest.approx(1.0)
    assert costly.equity.iloc[-1] < free.equity.iloc[-1]
    assert nse.equity.iloc[-1] < free.equity.iloc[-1]
    assert free.turnover.sum() > 1.0  # it does rebalance


def test_gate_off_means_cash_and_zero_return() -> None:
    prices = _prices(400, 5)
    off = pd.Series(False, index=prices.index)

    result, _ = mp.run_momentum_portfolio(prices, top_n=3, lookback=120, gate=off)

    assert (result.returns == 0).all()
    assert (result.weights.sum(axis=1) == 0).all()
    assert (result.rebalances["holdings"] == "cash").all()


def test_nothing_trending_up_goes_to_cash() -> None:
    idx = pd.bdate_range("2020-01-01", periods=300)
    falling = pd.DataFrame(
        {"A": np.linspace(200, 100, 300), "B": np.linspace(150, 90, 300)}, index=idx
    )

    result, _ = mp.run_momentum_portfolio(falling, top_n=2, lookback=100)

    assert (result.weights.sum(axis=1) == 0).all()


def test_weights_never_exceed_one_and_are_non_negative() -> None:
    result, bench = mp.run_momentum_portfolio(_prices(500, 6), top_n=4, lookback=150)

    for r in (result, bench):
        assert (r.weights >= -1e-12).all().all()
        # fees come out of equity, so a fully invested book can sit a hair above 100%
        assert (r.weights.sum(axis=1) <= 1.005).all()


def test_inverse_volatility_gives_the_calmer_name_more_weight() -> None:
    rng = np.random.default_rng(0)
    idx = pd.bdate_range("2020-01-01", periods=400)
    calm = 100 * np.exp(np.cumsum(rng.normal(0.001, 0.004, 400)))
    wild = 100 * np.exp(np.cumsum(rng.normal(0.001, 0.03, 400)))
    prices = pd.DataFrame({"CALM": calm, "WILD": wild}, index=idx)

    w = mp.momentum_target(2, 100, 10, weighting="inverse_volatility", require_positive=False)(
        prices
    )

    assert w.sum() == pytest.approx(1.0)
    assert w["CALM"] > w["WILD"]
    equal = mp.momentum_target(2, 100, 10, weighting="equal", require_positive=False)(prices)
    assert equal.tolist() == [0.5, 0.5]


def test_leader_is_selected() -> None:
    idx = pd.bdate_range("2020-01-01", periods=400)
    prices = pd.DataFrame(
        {
            "UP": 100 * np.exp(np.linspace(0, 1.0, 400)),
            "FLAT": np.full(400, 100.0),
            "DOWN": 100 * np.exp(np.linspace(0, -0.5, 400)),
        },
        index=idx,
    )

    w = mp.momentum_target(1, 200, 21)(prices)

    assert w.to_dict() == {"UP": 1.0, "FLAT": 0.0, "DOWN": 0.0}


def test_missing_history_is_not_selected_and_does_not_crash() -> None:
    prices = _prices(500, 4)
    prices.iloc[:300, 3] = np.nan  # listed late

    result, _ = mp.run_momentum_portfolio(prices, top_n=3, lookback=150)

    assert np.isfinite(result.returns).all()
    assert (result.weights.loc[: prices.index[299], "D"] == 0).all()


def test_validation_errors() -> None:
    prices = _prices(300, 3)
    with pytest.raises(ValueError):
        mp.clean_prices(pd.DataFrame())
    with pytest.raises(ValueError):
        mp.momentum_target(0, 100, 10)
    with pytest.raises(ValueError):
        mp.momentum_target(2, 100, 10, weighting="magic")
    with pytest.raises(ValueError):
        mp.run_momentum_portfolio(prices, lookback=400)
    with pytest.raises(ValueError):
        mp.run_momentum_portfolio(prices, lookback=100, rebalance_every=0)
    with pytest.raises(ValueError):
        mp.run_momentum_portfolio(prices, lookback=100, cost_bps=-1)


def test_performance_metrics_hand_computed() -> None:
    idx = pd.date_range("2024-01-01", periods=3, freq="D")
    m = mp.performance_metrics(pd.Series([0.1, -0.1, 0.1], index=idx))

    assert m["total_return"] == pytest.approx(1.1 * 0.9 * 1.1 - 1)
    assert m["max_drawdown"] == pytest.approx(-0.1)
