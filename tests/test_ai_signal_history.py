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


def test_neutral_records_market_movement_without_fabricating_strategy_return():
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

    assert pd.isna(history.loc[0, "return_pct"])
    assert history.loc[0, "market_return_pct"] == pytest.approx(10.0)


def test_neutral_horizon_outcome_keeps_actual_market_return():
    from ai_trading.signal_history import attach_horizon_outcomes

    record = record_signal(
        symbol="INFY",
        exchange="NSE",
        signal="NEUTRAL",
        probability_up=0.5,
        confidence_pct=50.0,
        validation_pct=60.0,
        trend_pct=50.0,
        entry_price=100.0,
        horizon_days=1,
        timestamp=datetime(2026, 10, 1, 9, 0, tzinfo=UTC),
    )
    index = pd.date_range("2026-10-01", periods=2, freq="B", tz="Asia/Kolkata")
    frame = pd.DataFrame({"Close": [100.0, 108.0]}, index=index)

    history = attach_horizon_outcomes([record], {"NSE:INFY": frame})

    assert bool(history.loc[0, "completed"]) is True
    assert pd.isna(history.loc[0, "return_pct"])
    assert history.loc[0, "market_return_pct"] == pytest.approx(8.0)


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


def test_neutral_summary_reports_underlying_move_not_strategy_win_rate():
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
    summary = summarize_outcomes(history)

    assert summary.loc[0, "signal"] == "NEUTRAL"
    assert summary.loc[0, "evaluated"] == 0
    assert pd.isna(summary.loc[0, "win_rate_pct"])
    assert summary.loc[0, "market_avg_return_pct"] == pytest.approx(10.0)
    assert summary.loc[0, "underlying_up_rate_pct"] == pytest.approx(100.0)


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


def test_horizon_outcome_uses_nth_future_trading_bar() -> None:
    from zoneinfo import ZoneInfo

    from ai_trading.signal_history import attach_horizon_outcomes

    record = record_signal(
        symbol="RELIANCE",
        exchange="NSE",
        signal="LONG",
        probability_up=0.7,
        confidence_pct=65.0,
        validation_pct=72.0,
        trend_pct=60.0,
        entry_price=100.0,
        horizon_days=2,
        timestamp=datetime(2026, 10, 1, 15, 30, tzinfo=ZoneInfo("Asia/Kolkata")),
    )
    index = pd.date_range("2026-10-01", periods=4, freq="B", tz="Asia/Kolkata")
    frame = pd.DataFrame({"Close": [100.0, 105.0, 110.0, 115.0]}, index=index)

    history = attach_horizon_outcomes([record], {"NSE:RELIANCE": frame})

    assert bool(history.loc[0, "completed"]) is True
    assert history.loc[0, "outcome_price"] == pytest.approx(110.0)
    assert history.loc[0, "return_pct"] == pytest.approx(10.0)
    assert history.loc[0, "outcome_timestamp"] == index[2]


def test_horizon_outcome_stays_pending_until_enough_future_bars_exist() -> None:
    from ai_trading.signal_history import attach_horizon_outcomes

    record = record_signal(
        symbol="TCS",
        exchange="NSE",
        signal="SHORT",
        probability_up=0.3,
        confidence_pct=70.0,
        validation_pct=75.0,
        trend_pct=35.0,
        entry_price=100.0,
        horizon_days=3,
        timestamp=datetime(2026, 10, 1, tzinfo=UTC),
    )
    index = pd.date_range("2026-10-02", periods=2, freq="B", tz="Asia/Kolkata")
    frame = pd.DataFrame({"Close": [95.0, 90.0]}, index=index)

    history = attach_horizon_outcomes([record], {"NSE:TCS": frame})

    assert bool(history.loc[0, "completed"]) is False
    assert pd.isna(history.loc[0, "outcome_price"])
    assert pd.isna(history.loc[0, "return_pct"])


def test_horizon_outcome_ignores_non_finite_prices() -> None:
    from ai_trading.signal_history import attach_horizon_outcomes

    record = record_signal(
        symbol="INFY",
        exchange="NSE",
        signal="LONG",
        probability_up=0.6,
        confidence_pct=60.0,
        validation_pct=65.0,
        trend_pct=55.0,
        entry_price=100.0,
        horizon_days=1,
        timestamp=datetime(2026, 10, 1, tzinfo=UTC),
    )
    index = pd.date_range("2026-10-02", periods=2, freq="B", tz="Asia/Kolkata")
    frame = pd.DataFrame({"Close": [float("inf"), 105.0]}, index=index)

    history = attach_horizon_outcomes([record], {"NSE:INFY": frame})

    assert bool(history.loc[0, "completed"]) is True
    assert history.loc[0, "outcome_price"] == pytest.approx(105.0)


def test_horizon_outcome_uses_adjusted_basis_across_a_split() -> None:
    from zoneinfo import ZoneInfo

    from ai_trading.signal_history import attach_horizon_outcomes

    record = record_signal(
        symbol="RELIANCE",
        exchange="NSE",
        signal="LONG",
        probability_up=0.7,
        confidence_pct=65.0,
        validation_pct=72.0,
        trend_pct=60.0,
        entry_price=100.0,
        adjusted_entry_price=50.0,
        horizon_days=1,
        timestamp=datetime(2026, 10, 1, 9, 0, tzinfo=ZoneInfo("Asia/Kolkata")),
    )
    index = pd.date_range("2026-10-01", periods=2, freq="B", tz="Asia/Kolkata")
    frame = pd.DataFrame(
        {"Close": [100.0, 50.0], "Adj Close": [50.0, 50.0]},
        index=index,
    )

    history = attach_horizon_outcomes([record], {"NSE:RELIANCE": frame})

    assert history.loc[0, "outcome_price"] == pytest.approx(50.0)
    assert history.loc[0, "return_pct"] == pytest.approx(0.0)


def test_daily_bar_on_signal_date_counts_when_signal_precedes_market_close() -> None:
    from zoneinfo import ZoneInfo

    from ai_trading.signal_history import attach_horizon_outcomes

    record = record_signal(
        symbol="HDFCBANK",
        exchange="NSE",
        signal="LONG",
        probability_up=0.65,
        confidence_pct=65.0,
        validation_pct=70.0,
        trend_pct=60.0,
        entry_price=100.0,
        horizon_days=1,
        timestamp=datetime(2026, 10, 1, 9, 0, tzinfo=ZoneInfo("Asia/Kolkata")),
    )
    index = pd.date_range("2026-10-01", periods=2, freq="B", tz="Asia/Kolkata")
    frame = pd.DataFrame({"Close": [105.0, 110.0]}, index=index)

    history = attach_horizon_outcomes([record], {"NSE:HDFCBANK": frame})

    assert bool(history.loc[0, "completed"]) is True
    assert history.loc[0, "outcome_price"] == pytest.approx(105.0)
    assert history.loc[0, "outcome_timestamp"] == index[0]
