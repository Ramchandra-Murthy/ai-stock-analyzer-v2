import pandas as pd
import pytest

from algorithmic_trading.trading_costs import IndiaEquityCostModel
from ai_trading.signal_trade_evaluation import (
    evaluate_signal_trades,
    summarize_signal_trade_evaluation,
)


def _history():
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=4, freq="D"),
            "symbol": ["AAA", "BBB", "CCC", "DDD"],
            "signal": ["LONG", "SHORT", "NEUTRAL", "LONG"],
            "horizon_days": [5, 5, 5, 5],
            "exchange": ["NSE", "NSE", "NSE", "BSE"],
            "completed": [True, True, True, False],
            "return_pct": [2.0, 1.0, float("nan"), 8.0],
            "benchmark_return_pct": [1.0, 2.0, 0.5, 1.0],
        }
    )


def _cost_model():
    return IndiaEquityCostModel(
        brokerage_bps=1.0,
        exchange_transaction_bps=2.0,
        regulatory_bps=1.0,
        stt_buy_bps=3.0,
        stt_sell_bps=4.0,
        stamp_duty_buy_bps=1.0,
        slippage_bps=5.0,
        gst_rate=0.18,
    )


def test_cost_adjusted_evaluation_applies_both_sides_of_round_trip():
    result = evaluate_signal_trades(_history(), _cost_model())

    assert len(result) == 2
    assert result.loc[0, "gross_return_pct"] == pytest.approx(2.0)
    assert result.loc[0, "estimated_cost_pct"] == pytest.approx(0.2744)
    assert result.loc[0, "net_return_pct"] == pytest.approx(1.7256)


def test_short_benchmark_is_direction_adjusted_before_excess_comparison():
    result = evaluate_signal_trades(_history(), _cost_model())
    short = result.loc[result["signal"] == "SHORT"].iloc[0]

    assert short["benchmark_return_pct"] == pytest.approx(2.0)
    assert short["directional_benchmark_return_pct"] == pytest.approx(-2.0)
    assert short["excess_return_pct"] == pytest.approx(3.7256)


def test_pending_neutral_and_nonfinite_outcomes_are_excluded():
    history = _history()
    history.loc[0, "return_pct"] = float("inf")
    result = evaluate_signal_trades(history, _cost_model())

    assert result.empty


def test_evaluation_without_benchmark_keeps_benchmark_metrics_missing():
    history = _history().iloc[[0]].drop(columns="benchmark_return_pct")
    result = evaluate_signal_trades(history, _cost_model())

    assert pd.isna(result.loc[0, "benchmark_return_pct"])
    assert pd.isna(result.loc[0, "excess_return_pct"])


def test_summary_reports_cost_drag_net_win_rate_and_benchmark_excess():
    evaluation = evaluate_signal_trades(_history(), _cost_model())
    summary = summarize_signal_trade_evaluation(evaluation)

    long_row = summary.loc[summary["signal"] == "LONG"].iloc[0]
    short_row = summary.loc[summary["signal"] == "SHORT"].iloc[0]
    assert long_row["avg_gross_return_pct"] == pytest.approx(2.0)
    assert long_row["avg_net_return_pct"] == pytest.approx(1.7256)
    assert long_row["net_win_rate_pct"] == pytest.approx(100.0)
    assert long_row["avg_excess_return_pct"] == pytest.approx(0.7256)
    assert short_row["avg_directional_benchmark_return_pct"] == pytest.approx(-2.0)


def test_empty_history_returns_stable_empty_schema():
    result = evaluate_signal_trades(pd.DataFrame(), _cost_model())

    assert result.empty
    assert "net_return_pct" in result.columns


def test_missing_required_columns_are_reported():
    with pytest.raises(ValueError, match="missing required columns"):
        evaluate_signal_trades(pd.DataFrame({"symbol": ["AAA"]}), _cost_model())
