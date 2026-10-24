"""India cost presets: exact arithmetic on the published rates, and sane behaviour."""

import pandas as pd
import pytest

from algorithmic_trading.trading_costs import (
    IndiaEquityCostModel,
    india_cost_model,
    round_trip_bps,
)


def test_delivery_round_trip_matches_hand_calculation() -> None:
    model = india_cost_model("delivery", slippage_bps=0.0)

    gst = 0.18 * (0.297 + 0.02)
    buy = 0.297 + 0.02 + gst + 10.0 + 1.5
    sell = 0.297 + 0.02 + gst + 10.0
    assert round_trip_bps(model) == pytest.approx(buy + sell, abs=1e-9)
    assert round_trip_bps(model) == pytest.approx(22.248, abs=1e-3)


def test_intraday_round_trip_matches_hand_calculation() -> None:
    model = india_cost_model("intraday", brokerage_bps=3.0, slippage_bps=0.0)

    gst = 0.18 * (3.0 + 0.297 + 0.02)
    per_side = 3.0 + 0.297 + 0.02 + gst
    expected = per_side + 0.3 + per_side + 2.5  # stamp on buy, STT on sell
    assert round_trip_bps(model) == pytest.approx(expected, abs=1e-9)


def test_stt_is_charged_on_the_right_sides() -> None:
    one, zero = pd.Series([1.0]), pd.Series([0.0])
    delivery = india_cost_model("delivery", slippage_bps=0.0)
    intraday = india_cost_model("intraday", brokerage_bps=0.0, slippage_bps=0.0)

    d_buy, d_sell = (
        float(delivery.cost_fraction(one, zero)[0]),
        float(delivery.cost_fraction(zero, one)[0]),
    )
    i_buy, i_sell = (
        float(intraday.cost_fraction(one, zero)[0]),
        float(intraday.cost_fraction(zero, one)[0]),
    )

    assert d_buy * 1e4 > 11 and d_sell * 1e4 > 10  # STT both sides
    assert i_buy * 1e4 < 1 < i_sell * 1e4  # intraday STT only on the sell side


def test_delivery_is_much_costlier_than_intraday_per_round_trip() -> None:
    assert round_trip_bps(india_cost_model("delivery")) > round_trip_bps(
        india_cost_model("intraday", brokerage_bps=0.0)
    )


def test_slippage_and_brokerage_are_overridable_and_additive() -> None:
    base = round_trip_bps(india_cost_model("delivery", slippage_bps=0.0))

    assert round_trip_bps(india_cost_model("delivery", slippage_bps=5.0)) == pytest.approx(
        base + 10.0
    )
    with_brokerage = round_trip_bps(
        india_cost_model("delivery", brokerage_bps=2.0, slippage_bps=0.0)
    )
    assert with_brokerage == pytest.approx(base + 2 * 2.0 * 1.18)  # brokerage carries 18% GST


def test_unknown_product_is_rejected() -> None:
    with pytest.raises(ValueError):
        india_cost_model("futures")


def test_zero_model_costs_nothing() -> None:
    assert round_trip_bps(IndiaEquityCostModel()) == 0.0
