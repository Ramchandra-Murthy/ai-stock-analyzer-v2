import numpy as np
import pandas as pd
import pytest

from algorithmic_trading.portfolio_tools import min_cvar_weights, portfolio_cvar, rebalance_plan
from algorithmic_trading.trading_costs import IndiaEquityCostModel, india_cost_model

ZERO_COST = IndiaEquityCostModel()


def _returns(n=400, seed=7):
    rng = np.random.default_rng(seed)
    calm = rng.normal(0.0004, 0.006, n)
    mid = rng.normal(0.0006, 0.011, n)
    wild = rng.normal(0.0009, 0.013, n)
    wild[rng.choice(n, 12, replace=False)] -= 0.07  # heavy left tail
    return pd.DataFrame(
        {"CALM": calm, "MID": mid, "WILD": wild}, index=pd.bdate_range("2022-01-01", periods=n)
    )


# ---------------------------------------------------------------- portfolio_cvar


def test_portfolio_cvar_is_the_mean_of_the_worst_days():
    frame = pd.DataFrame({"A": [-0.10, -0.08, 0.01, 0.02, 0.0, 0.03, 0.01, 0.0, -0.01, 0.02]})
    # level 0.8 on 10 days: the worst 2 days average a 9% loss
    assert portfolio_cvar(frame, pd.Series({"A": 1.0}), 0.8) == pytest.approx(0.09)


def test_portfolio_cvar_handles_a_fractional_tail():
    frame = pd.DataFrame({"A": [-0.10, -0.06, -0.02, 0.01, 0.02, 0.03, 0.01, 0.0, 0.01, 0.02]})
    # tail = 2.5 days: (10 + 6 + 0.5 * 2) / 2.5 percent
    assert portfolio_cvar(frame, pd.Series({"A": 1.0}), 0.75) == pytest.approx(0.068)


# ------------------------------------------------------------------ min_cvar


def test_min_cvar_weights_are_valid_and_beat_simple_alternatives():
    r = _returns()
    w, cvar = min_cvar_weights(r, 0.95)
    assert w.sum() == pytest.approx(1.0)
    assert (w >= -1e-12).all()
    assert cvar == pytest.approx(portfolio_cvar(r, w, 0.95))
    equal = pd.Series(1 / 3, index=r.columns)
    assert cvar <= portfolio_cvar(r, equal, 0.95) + 1e-12
    for name in r.columns:
        single = pd.Series({n: float(n == name) for n in r.columns})
        assert cvar <= portfolio_cvar(r, single, 0.95) + 1e-12


def test_min_cvar_is_not_beaten_by_random_portfolios():
    r = _returns()
    _, best = min_cvar_weights(r, 0.95)
    rng = np.random.default_rng(0)
    for raw in rng.dirichlet(np.ones(3), size=3000):
        assert portfolio_cvar(r, pd.Series(raw, index=r.columns), 0.95) >= best - 1e-9


def test_min_cvar_prefers_the_safe_asset_and_respects_the_cap():
    r = _returns()
    free, _ = min_cvar_weights(r, 0.95)
    assert free["CALM"] == free.max()
    capped, _ = min_cvar_weights(r, 0.95, max_weight=0.4)
    assert (capped <= 0.4 + 1e-9).all()
    assert capped.sum() == pytest.approx(1.0)


@pytest.mark.parametrize("bad", [0.3, 1.0])
def test_min_cvar_rejects_bad_levels(bad):
    with pytest.raises(ValueError):
        min_cvar_weights(_returns(), bad)


def test_min_cvar_rejects_thin_data_and_impossible_caps():
    with pytest.raises(ValueError, match="at least"):
        min_cvar_weights(_returns(30))
    with pytest.raises(ValueError, match="max_weight"):
        min_cvar_weights(_returns(), max_weight=0.2)
    with pytest.raises(ValueError, match="at least"):
        min_cvar_weights(_returns()[["CALM"]])


# ----------------------------------------------------------------- rebalance


def test_rebalance_exact_when_costs_are_zero():
    plan, summary = rebalance_plan(
        {"A": 100, "B": 0}, {"A": 100.0, "B": 50.0}, {"A": 0.5, "B": 0.5}, cost_model=ZERO_COST
    )
    assert plan.loc["A", "trade_shares"] == -50 and plan.loc["A", "action"] == "SELL"
    assert plan.loc["B", "trade_shares"] == 100 and plan.loc["B", "action"] == "BUY"
    assert summary["portfolio_value"] == pytest.approx(10_000)
    assert summary["turnover"] == pytest.approx(1.0)
    assert summary["cash_after"] == pytest.approx(0.0)
    assert summary["estimated_cost"] == 0.0
    assert plan["post_trade_weight"].sum() == pytest.approx(1.0)


def test_rebalance_never_spends_cash_it_does_not_have_when_costs_apply():
    plan, summary = rebalance_plan(
        {"A": 100, "B": 0}, {"A": 100.0, "B": 50.0}, {"A": 0.5, "B": 0.5}
    )
    assert summary["estimated_cost"] > 0
    assert summary["cash_after"] >= -1e-6
    assert plan.loc["B", "trade_shares"] < 100  # trimmed to pay the costs
    assert plan["est_cost"].sum() == pytest.approx(summary["estimated_cost"])


def test_rebalance_uses_available_cash_and_keeps_a_cash_target():
    plan, summary = rebalance_plan(
        {"A": 0}, {"A": 100.0}, {"A": 0.8}, cash=10_000.0, cost_model=ZERO_COST
    )
    assert plan.loc["A", "trade_shares"] == 80
    assert summary["cash_after"] == pytest.approx(2_000.0)


def test_rebalance_rounds_toward_zero_to_whole_lots():
    plan, _ = rebalance_plan(
        {"A": 0, "B": 0},
        {"A": 10.0, "B": 10.0},
        {"A": 0.5, "B": 0.5},
        cash=1_000.0,
        lot_sizes={"A": 30, "B": 1},
        cost_model=ZERO_COST,
    )
    assert plan.loc["A", "trade_shares"] == 30  # 50 wanted -> one lot of 30, not 60
    assert plan.loc["B", "trade_shares"] == 50


def test_rebalance_skips_trades_below_the_minimum_value():
    plan, summary = rebalance_plan(
        {"A": 50, "B": 50},
        {"A": 100.0, "B": 100.0},
        {"A": 0.51, "B": 0.49},
        min_trade_value=500.0,
        cost_model=ZERO_COST,
    )
    assert (plan["trade_shares"] == 0).all()
    assert summary["turnover"] == 0.0


def test_rebalance_adds_new_names_and_exits_removed_ones():
    plan, _ = rebalance_plan(
        {"OLD": 100}, {"OLD": 50.0, "NEW": 25.0}, {"NEW": 1.0}, cost_model=ZERO_COST
    )
    assert plan.loc["OLD", "post_trade_shares"] == 0
    assert plan.loc["NEW", "trade_shares"] == 200


@pytest.mark.parametrize(
    ("shares", "prices", "weights", "kwargs"),
    [
        ({"A": 1}, {"A": 10.0}, {"A": 0.7, "B": 0.5}, {}),  # sums above 1
        ({"A": 1}, {"A": 10.0}, {"A": -0.1}, {}),  # negative weight
        ({"A": 1.5}, {"A": 10.0}, {"A": 1.0}, {}),  # fractional shares
        ({"A": 1}, {"A": 0.0}, {"A": 1.0}, {}),  # bad price
        ({"A": 1}, {}, {"A": 1.0}, {}),  # missing price
        ({"A": 1}, {"A": 10.0}, {"A": 1.0}, {"cash": -1.0}),
        ({"A": 1}, {"A": 10.0}, {"A": 1.0}, {"lot_sizes": {"A": 0}}),
        ({"A": 0}, {"A": 10.0}, {"A": 1.0}, {}),  # nothing to rebalance
    ],
)
def test_rebalance_rejects_bad_inputs(shares, prices, weights, kwargs):
    with pytest.raises(ValueError):
        rebalance_plan(shares, prices, weights, **kwargs)


def test_rebalance_default_costs_match_the_delivery_model():
    plan, summary = rebalance_plan(
        {"A": 0}, {"A": 100.0}, {"A": 0.5}, cash=100_000.0, cost_model=india_cost_model("delivery")
    )
    buy = plan.loc["A", "trade_value"]
    assert summary["estimated_cost"] == pytest.approx(
        float(india_cost_model("delivery").cost_fraction(pd.Series([buy]), pd.Series([0.0]))[0])
    )
