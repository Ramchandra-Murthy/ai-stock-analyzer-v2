import numpy as np
import pandas as pd
import pytest

from algorithmic_trading import options_strategies as os_


def test_bull_call_spread_hand_computed():
    legs = [os_.Leg("call", 100, 6.0, 1), os_.Leg("call", 110, 2.0, -1)]
    s = os_.payoff_summary(legs)
    assert s["net_premium"] == 4.0
    assert s["max_loss"] == pytest.approx(4.0)
    assert s["max_profit"] == pytest.approx(6.0)
    assert s["breakevens"] == [104.0]
    assert os_.expiry_payoff(legs, 120.0) == pytest.approx(6.0)
    assert os_.expiry_payoff(legs, 90.0) == pytest.approx(-4.0)


def test_long_straddle_has_two_breakevens_and_unbounded_profit():
    legs = [os_.Leg("call", 100, 5.0, 1), os_.Leg("put", 100, 4.0, 1)]
    s = os_.payoff_summary(legs)
    assert s["max_profit"] is None
    assert s["max_loss"] == pytest.approx(9.0)
    assert s["breakevens"] == pytest.approx([91.0, 109.0])


def test_short_straddle_unbounded_loss():
    legs = [os_.Leg("call", 100, 5.0, -1), os_.Leg("put", 100, 4.0, -1)]
    s = os_.payoff_summary(legs)
    assert s["max_loss"] is None and s["max_profit"] == pytest.approx(9.0)
    assert s["breakevens"] == pytest.approx([91.0, 109.0])


def test_iron_condor_bounded_both_ways():
    legs = [
        os_.Leg("put", 90, 1.0, 1),
        os_.Leg("put", 95, 2.5, -1),
        os_.Leg("call", 105, 2.5, -1),
        os_.Leg("call", 110, 1.0, 1),
    ]
    s = os_.payoff_summary(legs)
    assert s["max_profit"] == pytest.approx(3.0)
    assert s["max_loss"] == pytest.approx(2.0)
    assert s["breakevens"] == pytest.approx([92.0, 108.0])


def test_summary_matches_dense_grid_for_random_strategies():
    rng = np.random.default_rng(0)
    grid = np.linspace(0, 400, 400001)
    for _ in range(30):
        legs = [
            os_.Leg(
                rng.choice(["call", "put"]),
                float(rng.integers(80, 121)),
                float(rng.uniform(0.5, 8)),
                int(rng.choice([-2, -1, 1, 2])),
            )
            for _ in range(rng.integers(1, 5))
        ]
        s = os_.payoff_summary(legs)
        pay = os_.expiry_payoff(legs, grid)
        if s["max_profit"] is not None:
            assert s["max_profit"] == pytest.approx(pay.max(), abs=1e-3)
        if s["max_loss"] is not None:
            assert s["max_loss"] == pytest.approx(max(-pay.min(), 0.0), abs=1e-3)
        for be in s["breakevens"]:
            assert abs(float(os_.expiry_payoff(legs, be))) < 1e-4


def test_leg_validation():
    for args in (("x", 100, 1, 1), ("call", -1, 1, 1), ("call", 100, -1, 1), ("call", 100, 1, 0)):
        with pytest.raises(ValueError):
            os_.Leg(*args)
    with pytest.raises(ValueError):
        os_.expiry_payoff([], 100)


def test_templates_shape_and_signs():
    kw = {
        "spot": 24_980,
        "strike_step": 50,
        "width_steps": 4,
        "days_to_expiry": 10,
        "rate": 0.065,
        "vol": 0.15,
    }
    for name in os_.TEMPLATES:
        legs = os_.build_template(name, **kw)
        assert 2 <= len(legs) <= 4
        assert all(l.premium > 0 for l in legs)
    assert os_.net_premium(os_.build_template("Long straddle", **kw)) > 0
    assert os_.net_premium(os_.build_template("Short straddle", **kw)) < 0
    assert os_.net_premium(os_.build_template("Iron condor", **kw)) < 0
    atm = [l.strike for l in os_.build_template("Long straddle", **kw)]
    assert atm == [25_000, 25_000]
    with pytest.raises(ValueError):
        os_.build_template("nope", **kw)
    with pytest.raises(ValueError):
        os_.build_template(
            "Long strangle", **{**kw, "spot": 100, "strike_step": 10, "width_steps": 20}
        )


def test_chain_premium_overrides_model():
    kw = {
        "spot": 100,
        "strike_step": 5,
        "width_steps": 1,
        "days_to_expiry": 10,
        "rate": 0.06,
        "vol": 0.2,
    }
    legs = os_.build_template("Long straddle", premium_lookup={("call", 100): 7.77}, **kw)
    assert legs[0].premium == 7.77 and legs[1].premium != 7.77


def test_greeks_signs_and_put_call_parity_of_delta():
    kw = {"spot": 100.0, "days_to_expiry": 30, "rate": 0.06, "vol": 0.2}
    long_straddle = [os_.Leg("call", 100, 1, 1), os_.Leg("put", 100, 1, 1)]
    g = os_.aggregate_greeks(long_straddle, **kw)
    assert abs(g["delta"]) < 0.15 and g["gamma"] > 0 and g["vega"] > 0 and g["theta"] < 0
    short = os_.aggregate_greeks([os_.Leg("call", 100, 1, -1), os_.Leg("put", 100, 1, -1)], **kw)
    assert short["gamma"] == pytest.approx(-g["gamma"])
    call = os_.aggregate_greeks([os_.Leg("call", 100, 1, 1)], **kw)["delta"]
    put = os_.aggregate_greeks([os_.Leg("put", 100, 1, 1)], **kw)["delta"]
    assert call - put == pytest.approx(1.0, abs=0.01)  # r>0, q=0: call delta - put delta = 1


def test_iv_rank_percentile():
    h = pd.Series(np.linspace(10, 30, 252))
    r = os_.iv_rank_percentile(h, current=20.0)
    assert r["rank"] == pytest.approx(0.5)
    assert r["percentile"] == pytest.approx(0.5, abs=0.01)
    assert os_.iv_rank_percentile(h, current=50)["rank"] == 1.0
    assert os_.iv_rank_percentile(pd.Series([15.0] * 60))["rank"] == 0.0
    with pytest.raises(ValueError):
        os_.iv_rank_percentile(pd.Series([1.0] * 5))
