import pytest

from engine.recommendation_validation import (
    reconcile_recommendations,
    validate_trade_plan,
)


def test_trade_plan_calculates_reward_risk_ratio():
    result = validate_trade_plan(
        current_price=157.0,
        target_price=166.28,
        stop_loss=144.0,
        min_reward_risk=1.0,
    )

    assert result["reward_per_unit"] == pytest.approx(9.28)
    assert result["risk_per_unit"] == pytest.approx(13.0)
    assert result["reward_risk_ratio"] == pytest.approx(9.28 / 13.0)
    assert result["valid"] is False
    assert "reward/risk ratio is below the configured minimum" in result["issues"]


@pytest.mark.parametrize(
    ("direction", "target", "stop", "expected_ratio"),
    [
        ("LONG", 110.0, 95.0, 2.0),
        ("SHORT", 90.0, 105.0, 2.0),
    ],
)
def test_trade_plan_supports_long_and_short(direction, target, stop, expected_ratio):
    result = validate_trade_plan(
        current_price=100.0,
        target_price=target,
        stop_loss=stop,
        direction=direction,
    )

    assert result["valid"] is True
    assert result["reward_risk_ratio"] == pytest.approx(expected_ratio)


@pytest.mark.parametrize(
    ("target", "stop"),
    [(90.0, 95.0), (110.0, 105.0)],
)
def test_trade_plan_rejects_wrong_orientation_for_long(target, stop):
    result = validate_trade_plan(
        current_price=100.0,
        target_price=target,
        stop_loss=stop,
        direction="LONG",
    )

    assert result["valid"] is False
    assert result["reward_risk_ratio"] is None


@pytest.mark.parametrize(
    ("price", "target", "stop"),
    [
        (0.0, 110.0, 95.0),
        (100.0, float("nan"), 95.0),
        (100.0, 110.0, float("inf")),
    ],
)
def test_trade_plan_rejects_invalid_prices(price, target, stop):
    with pytest.raises(ValueError):
        validate_trade_plan(
            current_price=price,
            target_price=target,
            stop_loss=stop,
        )


def test_reconciliation_flags_buy_sell_conflict_and_missing_risk():
    result = reconcile_recommendations(
        overall="HOLD",
        technical="SELL",
        fundamental="BUY",
        ai_verdict="INSUFFICIENT DATA",
        confidence=62,
        risk_level="Unknown",
        trade_plan={"valid": False},
    )

    assert result["conflict"] is True
    assert result["review_required"] is True
    assert "buy and sell recommendations conflict" in result["issues"]
    assert "AI verdict is unavailable or insufficient" in result["issues"]
    assert "risk level is missing or unknown" in result["issues"]
    assert "trade plan failed risk validation" in result["issues"]


def test_reconciliation_allows_consistent_complete_inputs():
    result = reconcile_recommendations(
        overall="BUY",
        technical="BUY",
        fundamental="BUY",
        ai_verdict="BUY",
        confidence=85,
        minimum_confidence=60,
        risk_level="MEDIUM",
        trade_plan={"valid": True},
    )

    assert result["conflict"] is False
    assert result["review_required"] is False
    assert result["issues"] == []


def test_reconciliation_rejects_invalid_confidence():
    with pytest.raises(ValueError):
        reconcile_recommendations(overall="HOLD", confidence=101)
