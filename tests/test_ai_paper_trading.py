"""Tests for the AI paper-trading portfolio engine."""

import pandas as pd
import pytest

from ai_trading.paper_trading import PaperPortfolio, apply_ml_signals
from ai_trading.risk import RiskLimits


def test_apply_long_signal_buys_and_marks_equity() -> None:
    portfolio = PaperPortfolio(initial_cash=100_000.0)
    signals = pd.DataFrame([{"symbol": "RELIANCE", "signal": "LONG", "confidence_pct": 80.0}])

    trades = apply_ml_signals(
        portfolio,
        signals,
        {"RELIANCE": 2_000.0},
        capital_fraction=0.20,
        max_positions=5,
    )

    assert len(trades) == 1
    assert trades[0].side == "BUY"
    assert portfolio.positions["RELIANCE"] == 10
    assert portfolio.equity({"RELIANCE": 2_100.0}) == pytest.approx(101_000.0)


def test_non_long_signal_closes_existing_position() -> None:
    portfolio = PaperPortfolio(initial_cash=100_000.0)
    portfolio.execute("TCS", "BUY", 10, 4_000.0)
    signals = pd.DataFrame([{"symbol": "TCS", "signal": "SHORT"}])

    trades = apply_ml_signals(portfolio, signals, {"TCS": 3_900.0})

    assert len(trades) == 1
    assert trades[0].side == "SELL"
    assert "TCS" not in portfolio.positions
    assert portfolio.cash == pytest.approx(99_000.0)


def test_position_limit_is_respected() -> None:
    portfolio = PaperPortfolio(initial_cash=100_000.0)
    signals = pd.DataFrame(
        [
            {"symbol": "A", "signal": "LONG", "confidence_pct": 90.0},
            {"symbol": "B", "signal": "LONG", "confidence_pct": 80.0},
            {"symbol": "C", "signal": "LONG", "confidence_pct": 70.0},
        ]
    )

    apply_ml_signals(
        portfolio,
        signals,
        {"A": 100.0, "B": 100.0, "C": 100.0},
        capital_fraction=0.90,
        max_positions=2,
    )

    assert set(portfolio.positions) == {"A", "B"}


def test_risk_limits_cap_new_position_allocation() -> None:
    portfolio = PaperPortfolio(initial_cash=100_000.0)
    signals = pd.DataFrame(
        [
            {"symbol": "A", "signal": "LONG", "confidence_pct": 90.0},
            {"symbol": "B", "signal": "LONG", "confidence_pct": 80.0},
        ]
    )

    apply_ml_signals(
        portfolio,
        signals,
        {"A": 1_000.0, "B": 1_000.0},
        capital_fraction=1.0,
        max_positions=2,
        risk_limits=RiskLimits(
            max_exposure_pct=50.0,
            max_position_pct=20.0,
            cash_reserve_pct=10.0,
        ),
    )

    assert portfolio.positions == {"A": 20, "B": 20}


@pytest.mark.parametrize("price", [float("nan"), float("inf"), float("-inf"), 0.0, -1.0])
def test_execute_rejects_non_finite_or_non_positive_prices(price: float) -> None:
    portfolio = PaperPortfolio(initial_cash=100_000.0)

    with pytest.raises(ValueError, match="price must be finite and positive"):
        portfolio.execute("RELIANCE", "BUY", 1, price)


@pytest.mark.parametrize("price", [float("nan"), float("inf"), float("-inf"), 0.0, -1.0])
def test_equity_rejects_non_finite_or_non_positive_mark_prices(price: float) -> None:
    portfolio = PaperPortfolio(initial_cash=100_000.0)
    portfolio.execute("RELIANCE", "BUY", 1, 100.0)

    with pytest.raises(ValueError, match="price for RELIANCE must be finite and positive"):
        portfolio.equity({"RELIANCE": price})
