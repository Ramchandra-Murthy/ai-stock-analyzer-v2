from datetime import UTC, datetime

import pandas as pd
import pytest

from ai_trading.signal_history import (
    attach_outcomes,
    record_signal,
    summarize_outcomes,
)


def test_record_signal_and_signed_outcome():
    record = record_signal(
        symbol="RELIANCE",
        exchange="NSE",
        signal="LONG",
        probability_up=0.7,
        confidence_pct=65.0,
        validation_pct=72.0,
        trend_pct=60.0,
        entry_price=100.0,
        horizon_days=5,
        timestamp=datetime(2026, 10, 1, tzinfo=UTC),
    )
    history = attach_outcomes([record], {"RELIANCE": 110.0})

    assert bool(history.loc[0, "completed"]) is True
    assert history.loc[0, "return_pct"] == pytest.approx(10.0)


def test_short_outcome_is_signed_correctly():
    record = record_signal(
        symbol="TCS",
        exchange="NSE",
        signal="SHORT",
        probability_up=0.3,
        confidence_pct=70.0,
        validation_pct=75.0,
        trend_pct=35.0,
        entry_price=100.0,
        horizon_days=5,
    )
    history = attach_outcomes([record], {"TCS": 90.0})

    assert history.loc[0, "return_pct"] == pytest.approx(10.0)


def test_neutral_has_zero_return():
    record = record_signal(
        symbol="INFY",
        exchange="NSE",
        signal="NEUTRAL",
        probability_up=0.5,
        confidence_pct=50.0,
        validation_pct=60.0,
        trend_pct=50.0,
        entry_price=100.0,
        horizon_days=5,
    )
    history = attach_outcomes([record], {"INFY": 110.0})

    assert history.loc[0, "return_pct"] == pytest.approx(0.0)


def test_summary_by_signal():
    records = [
        record_signal(
            symbol="A",
            exchange="NSE",
            signal="LONG",
            probability_up=0.7,
            confidence_pct=70.0,
            validation_pct=70.0,
            trend_pct=70.0,
            entry_price=100.0,
            horizon_days=5,
        ),
        record_signal(
            symbol="B",
            exchange="NSE",
            signal="LONG",
            probability_up=0.7,
            confidence_pct=70.0,
            validation_pct=70.0,
            trend_pct=70.0,
            entry_price=100.0,
            horizon_days=5,
        ),
    ]
    history = attach_outcomes(records, {"A": 110.0, "B": 95.0})
    summary = summarize_outcomes(history)

    assert isinstance(summary, pd.DataFrame)
    assert summary.loc[0, "signals"] == 2
    assert summary.loc[0, "win_rate_pct"] == pytest.approx(50.0)


def test_invalid_signal_is_rejected():
    with pytest.raises(ValueError):
        record_signal(
            symbol="ABC",
            exchange="NSE",
            signal="BUY",
            probability_up=0.6,
            confidence_pct=60.0,
            validation_pct=60.0,
            trend_pct=60.0,
            entry_price=100.0,
            horizon_days=5,
        )
