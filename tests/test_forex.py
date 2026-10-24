import numpy as np
import pandas as pd
import pytest

from forex import analytics as fa
from forex import backtest as fb
from forex import instruments as fi


def _fx(n=900, seed=0, drift=0.0, vol=0.004, start=1.10):
    r = np.random.default_rng(seed).normal(drift, vol, n)
    close = start * np.cumprod(1 + r)
    idx = pd.bdate_range("2020-01-01", periods=n)
    return pd.DataFrame(
        {"Open": close, "High": close * 1.002, "Low": close * 0.998, "Close": close}, index=idx
    )


def test_pair_parsing_and_pip_sizes():
    assert fi.normalise_pair("eur/usd") == "EURUSD" and fi.normalise_pair("USDINR=X") == "USDINR"
    assert fi.split_pair("GBPJPY") == ("GBP", "JPY") and fi.yahoo_symbol("eurusd") == "EURUSD=X"
    assert fi.pip_size("EURUSD") == 0.0001 and fi.pip_size("USDJPY") == 0.01
    for bad in ("EUR", "EURUSD1", "EUREUR", "12ABCD"):
        with pytest.raises(ValueError):
            fi.normalise_pair(bad)
    assert fi.price_to_pips("EURUSD", 0.0050) == pytest.approx(50)
    assert fi.pips_to_price("USDJPY", 25) == pytest.approx(0.25)


def test_position_size_hand_computed():
    # USD account, EURUSD, risk 1% of 10,000 = 100, stop 50 pips -> $0.0001*50 = $0.005/unit -> 20,000 units
    p = fi.position_size(
        "EURUSD",
        account_balance=10_000,
        risk_pct=0.01,
        stop_pips=50,
        quote_to_account=1.0,
        base_to_account=1.08,
    )
    assert p.units == pytest.approx(20_000) and p.lots == pytest.approx(0.2)
    assert p.pip_value_account == pytest.approx(2.0) and p.notional_account == pytest.approx(21_600)
    # INR account trading USDJPY: quote is JPY, 1 JPY = 0.56 INR; risk 10,000 INR, stop 40 pips = 0.40 JPY/unit = 0.224 INR
    j = fi.position_size(
        "USDJPY", account_balance=1_000_000, risk_pct=0.01, stop_pips=40, quote_to_account=0.56
    )
    assert j.units == pytest.approx(10_000 / 0.224) and np.isnan(j.notional_account)
    for kw in ({"risk_pct": 0}, {"stop_pips": 0}, {"account_balance": -1}, {"quote_to_account": 0}):
        args = {
            "account_balance": 1e4,
            "risk_pct": 0.01,
            "stop_pips": 50,
            "quote_to_account": 1.0,
        } | kw
        with pytest.raises(ValueError):
            fi.position_size("EURUSD", **args)


def test_spread_cost_and_margin():
    assert fi.spread_cost_fraction("EURUSD", 1.10, 1.1) == pytest.approx(0.00011 / 1.10)
    assert fi.margin_required(100_000, 20) == 5_000
    for bad in ((-1, 5), (1, 0.5)):
        with pytest.raises(ValueError):
            fi.margin_required(*bad)
    with pytest.raises(ValueError):
        fi.spread_cost_fraction("EURUSD", 0, 1)


def test_carry_sign_and_size():
    assert fa.daily_carry(0.05, 0.02, 365) == pytest.approx(0.03)
    assert fa.daily_carry(0.01, 0.05) < 0
    assert fa.annual_carry(0.065, 0.045) == pytest.approx(0.02)


def test_currency_strength_ranks_the_winner_and_is_causal():
    idx = pd.bdate_range("2024-01-01", periods=120)
    prices = pd.DataFrame(
        {
            "EURUSD": 1.1 * np.exp(np.linspace(0, 0.10, 120)),
            "EURJPY": 160 * np.exp(np.linspace(0, 0.15, 120)),
            "USDJPY": 145 * np.exp(np.linspace(0, 0.05, 120)),
        },
        index=idx,
    )
    s = fa.currency_strength(prices, 20)
    last = s.iloc[-1]
    assert last["EUR"] == last.max() and last["JPY"] == last.min()
    assert s.iloc[-1].sum() == pytest.approx(0.0, abs=1e-12)  # zero-sum across currencies
    pd.testing.assert_frame_equal(s.iloc[:80], fa.currency_strength(prices.iloc[:80], 20))
    with pytest.raises(ValueError):
        fa.currency_strength(prices, 1)


def test_atr_pips_and_correlation_and_overview():
    f = _fx(100)
    atr = fa.atr_pips(f, "EURUSD")
    assert atr.iloc[:13].isna().all() and 10 < atr.iloc[-1] < 200
    prices = pd.DataFrame({"EURUSD": _fx(200, 1)["Close"], "GBPUSD": _fx(200, 2)["Close"]})
    c = fa.correlation_matrix(prices)
    assert c.loc["EURUSD", "EURUSD"] == pytest.approx(1.0)
    with pytest.raises(ValueError):
        fa.correlation_matrix(prices.iloc[:10])
    ov = fa.pair_overview(prices)
    assert set(ov["Trend"]) <= {"Up", "Down", "Range"}


def test_backtest_costs_carry_and_leverage():
    f = _fx(900, 3)
    free = fb.run_fx_backtest(f, "EURUSD", "Supertrend", spread_pips=0)
    costly = fb.run_fx_backtest(f, "EURUSD", "Supertrend", spread_pips=5)
    assert costly.metrics["total_return"] < free.metrics["total_return"]
    pos = free.curve["position"]
    carry = fb.run_fx_backtest(
        f, "EURUSD", "Supertrend", spread_pips=0, base_rate=0.05, quote_rate=0.0
    )
    # carry contribution matches position * rate * calendar days / 365, summed
    gaps = pd.Series(f.index, index=f.index).diff().dt.days.fillna(1.0)
    assert carry.carry_return.sum() == pytest.approx(
        (pos * 0.05 * gaps / 365).reindex(carry.carry_return.index).sum()
    )
    lev = fb.run_fx_backtest(f, "EURUSD", "Supertrend", spread_pips=0, leverage=3)
    assert lev.returns.std() == pytest.approx(3 * free.returns.std(), rel=1e-6)
    assert free.trades > 0
    with pytest.raises(ValueError):
        fb.run_fx_backtest(f, "EURUSD", "Supertrend", leverage=100)
    with pytest.raises(ValueError):
        fb.run_fx_backtest(f, "EURUSD", "Nope")


def test_backtest_no_lookahead_and_long_only_option():
    f = _fx(900, 4)
    base = fb.run_fx_backtest(f, "EURUSD", "Donchian breakout")
    altered = f.copy()
    altered.iloc[700:, :4] *= np.linspace(1, 2, 200)[:, None]
    changed = fb.run_fx_backtest(altered, "EURUSD", "Donchian breakout")
    t = f.index[700]
    pd.testing.assert_series_equal(
        base.returns[base.returns.index < t], changed.returns[changed.returns.index < t]
    )
    long_only = fb.run_fx_backtest(f, "EURUSD", "Donchian breakout", allow_short=False)
    assert (long_only.curve["position"] >= 0).all() and (base.curve["position"] < 0).any()


def test_compare_strategies_table():
    t = fb.compare_fx_strategies(
        _fx(900, 5), "EURUSD", ("Supertrend", "Donchian breakout", "Z-score mean reversion")
    )
    assert len(t) == 3 and t["sharpe"].is_monotonic_decreasing
