import numpy as np
import pytest

from algorithmic_trading.execution import (
    pov_schedule,
    simulate_execution,
    square_root_impact,
    twap_schedule,
    u_shaped_profile,
    vwap_schedule,
)


def test_schedules_sum_exactly_to_the_order():
    assert twap_schedule(1003, 7).sum() == 1003
    assert vwap_schedule(1003, u_shaped_profile(9)).sum() == 1003
    assert list(twap_schedule(10, 4)) == [3, 3, 2, 2]


def test_u_shape_is_heavier_at_the_ends():
    p = u_shaped_profile(11)
    assert p[0] > p[5] < p[-1] and p.sum() == pytest.approx(1.0)


def test_pov_respects_participation_and_can_leave_a_remainder():
    out = pov_schedule(10_000, [1000] * 5, 0.10)
    assert list(out) == [100] * 5  # 10% of each slice; 9,500 shares unfilled
    full = pov_schedule(250, [1000] * 5, 0.10)
    assert full.sum() == 250


def test_impact_follows_square_root_law():
    one = square_root_impact(10_000, 1_000_000, 0.02)
    four = square_root_impact(40_000, 1_000_000, 0.02)
    assert four == pytest.approx(2 * one)
    assert square_root_impact(0, 1_000_000, 0.02) == 0


def test_splitting_reduces_impact_on_a_flat_market():
    px, vol = np.full(10, 100.0), np.full(10, 50_000.0)
    kw = {"adv": 500_000, "daily_vol": 0.02, "half_spread_bps": 0.0}
    one = simulate_execution("buy", [50_000] + [0] * 9, px, vol, **kw)
    ten = simulate_execution("buy", twap_schedule(50_000, 10), px, vol, **kw)
    assert ten.impact_bps < one.impact_bps
    assert ten.drift_bps == pytest.approx(0.0)


def test_buy_in_a_rising_market_pays_drift_and_sell_gains_from_it():
    px = np.linspace(100, 101, 10)
    vol = np.full(10, 10_000.0)
    kw = {"adv": 1e9, "daily_vol": 0.0, "half_spread_bps": 0.0}
    buy = simulate_execution("buy", twap_schedule(1000, 10), px, vol, **kw)
    sell = simulate_execution("sell", twap_schedule(1000, 10), px, vol, **kw)
    assert buy.shortfall_bps > 0 > sell.shortfall_bps
    assert buy.shortfall_rupees == pytest.approx(-sell.shortfall_rupees)


def test_rupee_shortfall_matches_hand_calculation():
    r = simulate_execution(
        "buy", [100, 100], [100.0, 102.0], [1.0, 1.0], adv=1e9, daily_vol=0.0, half_spread_bps=0.0
    )
    assert r.shortfall_rupees == pytest.approx(200.0)  # 100 shares * 2 rupees above arrival
    assert r.average_price == pytest.approx(101.0)


@pytest.mark.parametrize(
    "call",
    [
        lambda: twap_schedule(10, 0),
        lambda: pov_schedule(10, [1], 0.9),
        lambda: square_root_impact(1, 0, 0.02),
        lambda: simulate_execution("hold", [1], [1.0], [1.0], adv=1, daily_vol=0.01),
        lambda: simulate_execution("buy", [0], [1.0], [1.0], adv=1, daily_vol=0.01),
        lambda: simulate_execution("buy", [1, 1], [1.0], [1.0], adv=1, daily_vol=0.01),
        lambda: simulate_execution("buy", [1], [-1.0], [1.0], adv=1, daily_vol=0.01),
    ],
)
def test_bad_inputs_raise(call):
    with pytest.raises(ValueError):
        call()
