import numpy as np
import pandas as pd
import pytest

from crypto import analytics as ca
from crypto import backtest as cb
from crypto import instruments as ci


def _px(n=1200, seed=0, drift=0.0008, vol=0.035):
    r = np.random.default_rng(seed).normal(drift, vol, n)
    close = 20_000 * np.cumprod(1 + r)
    idx = pd.date_range("2020-01-01", periods=n, freq="D")  # crypto trades daily including weekends
    return pd.DataFrame(
        {"Open": close, "High": close * 1.02, "Low": close * 0.98, "Close": close}, index=idx
    )


def test_symbols_and_quote_rules():
    assert ci.yahoo_symbol("btc") == "BTC-USD" and ci.yahoo_symbol("eth", "inr") == "ETH-INR"
    for bad in (("SOL", "INR"), ("BTC", "EUR"), ("B T", "USD")):
        with pytest.raises(ValueError):
            ci.yahoo_symbol(*bad)


def test_fee_model_hand_computed():
    f = ci.FeeModel(taker_bps=10, maker_bps=5, slippage_bps=10, gst_rate=0.18)
    assert f.per_side_bps() == pytest.approx(
        10 * 1.18 + 10
    ) and f.round_trip_bps() == pytest.approx(43.6)
    assert (
        ci.FeeModel(
            taker_bps=10, maker_bps=5, slippage_bps=0, gst_rate=0, use_maker=True
        ).per_side_bps()
        == 5
    )
    with pytest.raises(ValueError):
        ci.FeeModel(taker_bps=-1)


def test_tax_has_no_loss_relief():
    assert ci.tax_on_gain(100) == pytest.approx(31.2) and ci.tax_on_gain(-100) == 0.0


def test_risk_overview_properties_and_validation():
    c = _px()["Close"]
    r = ca.risk_overview(c)
    assert r["annual_volatility"] == pytest.approx(c.pct_change().std() * np.sqrt(365))
    assert r["max_drawdown"] <= r["drawdown_from_high"] <= 0 and r["worst_day"] < 0 < r["best_day"]
    with pytest.raises(ValueError):
        ca.risk_overview(c.iloc[:10])


def test_dca_on_flat_and_rising_prices():
    idx = pd.date_range("2022-01-01", periods=70, freq="D")
    flat = ca.dca_simulation(pd.Series(100.0, index=idx), 1000, 7)
    assert flat["buys"] == 10 and flat["invested"] == 10_000 and flat["return"] == pytest.approx(0)
    rising = pd.Series(np.linspace(100, 200, 70), index=idx)
    r = ca.dca_simulation(rising, 1000, 7)
    assert r["lumpsum_return"] > r["return"] > 0 and r["average_cost"] < 200
    with pytest.raises(ValueError):
        ca.dca_simulation(rising, 0)


def test_liquidation_and_funding_hand_values():
    assert ca.liquidation_price(100, 10, long=True, maintenance_margin=0.005) == pytest.approx(90.5)
    assert ca.liquidation_price(100, 10, long=False, maintenance_margin=0.005) == pytest.approx(
        109.5
    )
    assert ca.liquidation_price(100, 1, long=True, maintenance_margin=0) == 0.0
    assert ca.liquidation_price(100, 20) > ca.liquidation_price(
        100, 5
    )  # more leverage, closer to entry
    assert ca.funding_cost(10_000, 0.0001, 10, long=True) == pytest.approx(30.0)
    assert ca.funding_cost(10_000, 0.0001, 10, long=False) == pytest.approx(-30.0)
    for bad in ((100, 0.5), (-1, 5)):
        with pytest.raises(ValueError):
            ca.liquidation_price(*bad)


def test_position_size():
    p = ca.position_size(10_000, 0.01, 50_000, 49_000)
    assert p["quantity"] == pytest.approx(0.1) and p["notional"] == pytest.approx(5_000)
    assert p["leverage_needed"] == pytest.approx(0.5)
    with pytest.raises(ValueError):
        ca.position_size(10_000, 0.01, 100, 100)


def test_after_tax_is_worse_and_asymmetric():
    # +10% then -10%: pre-tax 0.99 growth, post-tax pays tax on the win, no relief on the loss
    s = cb.after_tax_summary(pd.Series([0.10, -0.10]), 1000)
    assert s["pre_tax_final"] == pytest.approx(990)
    assert s["tax_paid"] == pytest.approx(100 * 0.312)
    assert s["after_tax_final"] == pytest.approx((1000 + 100 - 31.2) * 0.9)
    assert cb.after_tax_summary(pd.Series([-0.1, -0.1]), 1000)["tax_paid"] == 0
    assert cb.after_tax_summary(pd.Series(dtype=float), 1000)["after_tax_final"] == 1000


def test_trade_returns_hand_case():
    pos = pd.Series([0, 1, 1, 0, 1, 1])
    ret = pd.Series([0, 0.1, 0.1, 0, -0.05, 0.0])
    t = cb.trade_returns(pos, ret)
    assert t.tolist() == pytest.approx([1.1 * 1.1 - 1, 0.95 - 1])


def test_backtest_costs_hurt_and_365_metrics_used():
    f = _px(1200, 3)
    free = cb.run_crypto_backtest(f, "Supertrend", fees=ci.FeeModel(0, 0, 0, 0))
    costly = cb.run_crypto_backtest(f, "Supertrend", fees=ci.FeeModel(50, 50, 50))
    assert costly.metrics["total_return"] < free.metrics["total_return"]
    r = free.curve["strategy_return"]
    assert free.metrics["volatility"] == pytest.approx(r.std() * np.sqrt(365))
    assert free.after_tax["after_tax_return"] <= free.after_tax["pre_tax_return"] + 1e-12
    assert len(free.trade_returns) > 2


def test_backtest_no_lookahead_and_spot_is_long_only():
    f = _px(1200, 4)
    base = cb.run_crypto_backtest(f, "Donchian breakout")
    altered = f.copy()
    altered.iloc[900:, :4] *= np.linspace(1, 2, 300)[:, None]
    changed = cb.run_crypto_backtest(altered, "Donchian breakout")
    t = f.index[900]
    a, b = base.curve["strategy_return"], changed.curve["strategy_return"]
    pd.testing.assert_series_equal(a[a.index < t], b[b.index < t])
    assert (base.curve["position"] >= 0).all()
    with pytest.raises(ValueError):
        cb.run_crypto_backtest(f, "Nope")


def test_compare_table():
    t = cb.compare_crypto_strategies(
        _px(1200, 5), ("Supertrend", "Donchian breakout", "Z-score mean reversion")
    )
    assert len(t) == 3 and t["sharpe"].is_monotonic_decreasing and "buy_hold_return" in t
