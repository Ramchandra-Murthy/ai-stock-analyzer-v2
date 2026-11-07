import pandas as pd
import pytest

from ai_trading.signal_performance import summarize_signal_performance


def _history(returns):
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=len(returns), freq="D"),
            "signal": ["LONG"] * len(returns),
            "horizon_days": [5] * len(returns),
            "exchange": ["NSE"] * len(returns),
            "completed": [True] * len(returns),
            "return_pct": returns,
        }
    )


def test_performance_metrics_count_break_even_separately():
    result = summarize_signal_performance(_history([10.0, -5.0, 0.0])).iloc[0]
    assert result["completed"] == 3
    assert result["wins"] == 1
    assert result["losses"] == 1
    assert result["breakeven"] == 1
    assert result["win_rate_pct"] == pytest.approx(100.0 / 3.0)
    assert result["avg_return_pct"] == pytest.approx(5.0 / 3.0)
    assert result["expectancy_pct"] == pytest.approx(5.0 / 3.0)
    assert result["profit_factor"] == pytest.approx(2.0)
    assert result["longest_losing_streak"] == 1


def test_performance_metrics_exclude_pending_and_non_finite_rows():
    history = _history([10.0, float("inf"), -5.0])
    history.loc[2, "completed"] = False
    result = summarize_signal_performance(history).iloc[0]
    assert result["completed"] == 1
    assert result["avg_return_pct"] == pytest.approx(10.0)


def test_performance_metrics_report_wilson_interval_and_drawdown():
    result = summarize_signal_performance(_history([10.0, -20.0, 5.0])).iloc[0]
    assert 0.0 <= result["win_rate_ci_low_pct"] <= result["win_rate_pct"]
    assert result["win_rate_pct"] <= result["win_rate_ci_high_pct"] <= 100.0
    assert result["max_drawdown_pct"] == pytest.approx(-20.0)


def test_profit_factor_is_undefined_without_losses():
    result = summarize_signal_performance(_history([1.0, 2.0])).iloc[0]
    assert pd.isna(result["profit_factor"])


def test_performance_groups_by_signal_horizon_and_exchange():
    history = _history([2.0, -1.0])
    second = history.iloc[[0]].copy()
    second["exchange"] = "BSE"
    second["horizon_days"] = 10
    result = summarize_signal_performance(pd.concat([history, second], ignore_index=True))
    assert len(result) == 2
    assert set(result["exchange"]) == {"NSE", "BSE"}


def test_neutral_market_movement_is_not_counted_as_strategy_performance():
    history = _history([float("nan")])
    history["signal"] = "NEUTRAL"
    result = summarize_signal_performance(history)
    assert result.empty
