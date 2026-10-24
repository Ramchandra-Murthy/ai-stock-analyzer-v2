import pandas as pd
import pytest

from algorithmic_trading.backtester import run_backtest
from algorithmic_trading.trading_costs import IndiaEquityCostModel


def test_backtest_applies_signal_on_next_bar() -> None:
    prices = pd.Series(
        [100.0, 110.0, 121.0],
        index=pd.date_range("2026-01-01", periods=3, freq="D"),
    )
    signals = pd.Series([1.0, 1.0, 0.0], index=prices.index)

    result, metrics = run_backtest(
        prices,
        signals,
        initial_capital=100_000,
        cost_bps=0,
    )

    assert result["position"].tolist() == [0.0, 1.0, 1.0]
    assert metrics.total_return == pytest.approx(0.21)


def test_transaction_cost_reduces_returns() -> None:
    index = pd.date_range("2026-01-01", periods=3, freq="D")
    prices = pd.Series([100.0, 110.0, 110.0], index=index)
    signals = pd.Series([1.0, 1.0, 0.0], index=index)

    _, free = run_backtest(prices, signals, cost_bps=0)
    _, charged = run_backtest(prices, signals, cost_bps=100)

    assert charged.total_return < free.total_return


def test_reversal_starts_a_new_directional_trade() -> None:
    index = pd.date_range("2026-01-01", periods=4, freq="D")
    prices = pd.Series([100.0, 110.0, 99.0, 99.0], index=index)
    signals = pd.Series([1.0, -1.0, 0.0, 0.0], index=index)

    _, metrics = run_backtest(prices, signals, cost_bps=0)

    assert metrics.trade_count == 2
    assert metrics.win_rate == pytest.approx(1.0)


def test_invalid_inputs_fail() -> None:
    index = pd.date_range("2026-01-01", periods=2, freq="D")
    prices = pd.Series([100.0, 101.0], index=index)
    signals = pd.Series([1.0, 0.0], index=index)

    with pytest.raises(ValueError, match="initial_capital"):
        run_backtest(prices, signals, initial_capital=0)

    for invalid_capital in (float("nan"), float("inf")):
        with pytest.raises(ValueError, match="initial_capital"):
            run_backtest(prices, signals, initial_capital=invalid_capital)

    for invalid_cost in (float("nan"), float("inf")):
        with pytest.raises(ValueError, match="cost_bps"):
            run_backtest(prices, signals, cost_bps=invalid_cost)


def test_cost_model_charges_buy_and_sell_turnover_separately() -> None:
    index = pd.date_range("2026-01-01", periods=4, freq="D")
    prices = pd.Series([100.0, 100.0, 100.0, 100.0], index=index)
    signals = pd.Series([1.0, 1.0, -1.0, 0.0], index=index)
    model = IndiaEquityCostModel(
        brokerage_bps=1.0,
        exchange_transaction_bps=1.0,
        stt_sell_bps=2.0,
        stamp_duty_buy_bps=1.0,
        slippage_bps=1.0,
        gst_rate=0.18,
    )

    data, metrics = run_backtest(prices, signals, cost_model=model)

    assert data["buy_turnover"].tolist() == pytest.approx([0.0, 1.0, 0.0, 0.0])
    assert data["sell_turnover"].tolist() == pytest.approx([0.0, 0.0, 0.0, 2.0])
    assert data["transaction_cost"].iloc[1] > 0
    assert data["transaction_cost"].iloc[3] > data["transaction_cost"].iloc[1]
    assert metrics.total_return < 0


def test_india_equity_cost_model_rejects_negative_rates() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        IndiaEquityCostModel(brokerage_bps=-1.0)


def test_india_equity_cost_model_rejects_non_finite_rates() -> None:
    for invalid_rate in (float("nan"), float("inf")):
        with pytest.raises(ValueError, match="finite"):
            IndiaEquityCostModel(brokerage_bps=invalid_rate)

    for invalid_rate in (float("nan"), float("inf")):
        with pytest.raises(ValueError, match="gst_rate"):
            IndiaEquityCostModel(gst_rate=invalid_rate)


def test_risk_metrics_are_populated_for_variable_returns() -> None:
    index = pd.date_range("2026-01-01", periods=5, freq="D")
    prices = pd.Series([100.0, 102.0, 101.0, 104.0, 103.0], index=index)
    signals = pd.Series([1.0, 1.0, 1.0, 1.0, 0.0], index=index)

    _, metrics = run_backtest(prices, signals, cost_bps=0)

    assert metrics.volatility > 0
    assert metrics.sharpe_ratio is not None
    assert metrics.sortino_ratio is not None
    assert metrics.calmar_ratio is not None


def test_risk_ratios_are_none_when_returns_have_no_variation_or_downside() -> None:
    index = pd.date_range("2026-01-01", periods=4, freq="D")
    prices = pd.Series([100.0, 100.0, 100.0, 100.0], index=index)
    signals = pd.Series([0.0, 0.0, 0.0, 0.0], index=index)

    _, metrics = run_backtest(prices, signals, cost_bps=0)

    assert metrics.volatility == pytest.approx(0.0)
    assert metrics.sharpe_ratio is None
    assert metrics.sortino_ratio is None
    assert metrics.calmar_ratio is None


def test_backtest_sorts_unordered_timestamps_before_returns() -> None:
    index = pd.date_range("2026-01-01", periods=4, freq="D")
    prices = pd.Series([100.0, 110.0, 121.0, 133.1], index=index).iloc[[2, 0, 3, 1]]
    signals = pd.Series(1.0, index=index).iloc[[2, 0, 3, 1]]

    data, metrics = run_backtest(prices, signals, cost_bps=0)

    assert data.index.is_monotonic_increasing
    assert metrics.total_return == pytest.approx(0.331)


def test_backtest_rejects_duplicate_price_timestamps() -> None:
    index = pd.date_range("2026-01-01", periods=3, freq="D")
    prices = pd.Series([100.0, 101.0, 102.0], index=index)
    prices = pd.concat([prices, prices.iloc[[1]]])
    signals = pd.Series(1.0, index=prices.index)

    with pytest.raises(ValueError, match="duplicate timestamps"):
        run_backtest(prices, signals, cost_bps=0)


def test_backtest_rejects_duplicate_signal_timestamps() -> None:
    index = pd.date_range("2026-01-01", periods=3, freq="D")
    prices = pd.Series([100.0, 101.0, 102.0], index=index)
    signals = pd.Series(1.0, index=index)
    signals = pd.concat([signals, signals.iloc[[1]]])

    with pytest.raises(ValueError, match="duplicate timestamps"):
        run_backtest(prices, signals, cost_bps=0)


def test_backtest_rejects_non_finite_price_instead_of_bridging_gap() -> None:
    index = pd.date_range("2026-01-01", periods=5, freq="D")
    prices = pd.Series([100.0, float("inf"), 110.0, 121.0, 133.1], index=index)
    signals = pd.Series(1.0, index=index)

    with pytest.raises(ValueError, match="prices must be finite"):
        run_backtest(prices, signals, cost_bps=0)


def test_backtest_rejects_non_finite_signal_instead_of_bridging_gap() -> None:
    index = pd.date_range("2026-01-01", periods=5, freq="D")
    prices = pd.Series([100.0, 101.0, 102.0, 103.0, 104.0], index=index)
    signals = pd.Series([1.0, 1.0, float("nan"), 1.0, 1.0], index=index)

    with pytest.raises(ValueError, match="signals must be finite"):
        run_backtest(prices, signals, cost_bps=0)


def test_backtest_requires_two_aligned_observations() -> None:
    prices = pd.Series([100.0], index=pd.to_datetime(["2026-01-01"]))
    signals = pd.Series([1.0], index=prices.index)

    with pytest.raises(ValueError, match="at least two aligned price observations"):
        run_backtest(prices, signals, cost_bps=0)


def test_compare_timeframe_backtests_uses_shared_cost_assumptions() -> None:
    from algorithmic_trading.backtester import compare_timeframe_backtests

    index = pd.date_range("2026-01-01", periods=4, freq="D")
    prices = pd.Series([100.0, 102.0, 101.0, 104.0], index=index)
    signals = pd.Series([1.0, 1.0, 1.0, 0.0], index=index)

    comparison = compare_timeframe_backtests(
        {"5min": (prices, signals), "15min": (prices, signals)},
        cost_bps=0,
    )

    assert comparison.index.tolist() == ["5min", "15min"]
    assert comparison.loc["5min", "total_return"] == pytest.approx(
        comparison.loc["15min", "total_return"]
    )
    assert comparison.loc["5min", "trade_count"] == comparison.loc["15min", "trade_count"]
    assert "max_drawdown" in comparison.columns
    assert "sharpe_ratio" in comparison.columns


def test_compare_timeframe_backtests_rejects_empty_input() -> None:
    from algorithmic_trading.backtester import compare_timeframe_backtests

    with pytest.raises(ValueError, match="at least one timeframe"):
        compare_timeframe_backtests({})
