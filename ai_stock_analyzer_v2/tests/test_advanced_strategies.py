"""Tests for the systematic strategy library.

The most important property is causality: a signal on bar *t* may not change when bars
after *t* are added. A violation would mean look-ahead bias and inflated backtests.
"""

import numpy as np
import pandas as pd
import pytest

from algorithmic_trading import advanced_strategies as strat
from algorithmic_trading.backtester import run_backtest


def _ohlc(close, spread: float = 0.5) -> pd.DataFrame:
    close = pd.Series(np.asarray(close, dtype=float))
    close.index = pd.bdate_range("2024-01-01", periods=len(close))
    return pd.DataFrame(
        {"Open": close, "High": close + spread, "Low": close - spread, "Close": close}
    )


def _trend_then_reversal(n_up: int = 80, n_down: int = 80) -> pd.DataFrame:
    up = 100 + np.arange(n_up) * 1.0
    down = up[-1] - np.arange(1, n_down + 1) * 1.0
    return _ohlc(np.concatenate([up, down]))


def _noisy_walk(n: int = 400, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0.0004, 0.012, n)))
    return _ohlc(close, spread=0.8)


# ---------------------------------------------------------------- ATR / Supertrend
def test_atr_is_nan_during_warmup_and_does_not_mutate_input() -> None:
    frame = _noisy_walk(60)
    before = frame.copy()

    atr = strat.average_true_range(frame, 14)

    assert atr.iloc[:13].isna().all()
    assert (atr.iloc[13:] > 0).all()
    pd.testing.assert_frame_equal(frame, before)


def test_supertrend_follows_trend_and_flips_on_reversal() -> None:
    result = strat.supertrend(_trend_then_reversal(), period=10, multiplier=3.0)

    assert (result["direction"].iloc[:9] == 0).all()  # warm-up
    assert result["direction"].iloc[60] == 1
    assert result["direction"].iloc[-1] == -1
    up = result[result["direction"] == 1]
    assert (up["supertrend"] <= _trend_then_reversal().loc[up.index, "Close"]).all()


def test_supertrend_signals_long_only_by_default() -> None:
    signals = strat.supertrend_signals(_trend_then_reversal())

    assert set(signals.unique()) <= {0.0, 1.0}
    assert signals.iloc[60] == 1.0
    assert signals.iloc[-1] == 0.0


def test_supertrend_signals_can_go_short() -> None:
    signals = strat.supertrend_signals(_trend_then_reversal(), allow_short=True)

    assert signals.iloc[-1] == -1.0


# ---------------------------------------------------------------- Donchian breakout
def test_donchian_enters_on_breakout_and_exits_on_breakdown() -> None:
    flat = [100.0] * 30
    rally = [100.0 + i for i in range(1, 16)]
    selloff = [rally[-1] - 2 * i for i in range(1, 16)]
    signals = strat.donchian_breakout_signals(_ohlc(flat + rally + selloff), 20, 10)

    assert signals.iloc[29] == 0.0  # still inside the channel
    assert signals.iloc[30] == 1.0  # first close above the prior 20-bar high
    assert signals.iloc[-1] == 0.0  # stopped out by the 10-bar low


def test_donchian_short_side_is_opt_in() -> None:
    frame = _ohlc([100.0] * 30 + [100.0 - i for i in range(1, 20)])

    assert (strat.donchian_breakout_signals(frame, 20, 10) == 0.0).all()
    assert strat.donchian_breakout_signals(frame, 20, 10, allow_short=True).iloc[-1] == -1.0


# ---------------------------------------------------------------- mean reversion
def test_zscore_buys_a_dip_and_exits_on_recovery() -> None:
    close = pd.Series([100.0, 101.0] * 15 + [90.0, 92.0, 97.0, 100.0, 101.0, 100.0])
    signals = strat.zscore_mean_reversion_signals(close, window=20, entry_z=2.0, exit_z=0.5)

    assert signals.iloc[30] == 1.0  # the plunge to 90
    assert signals.iloc[-1] == 0.0  # recovered


def test_zscore_rejects_invalid_thresholds() -> None:
    with pytest.raises(ValueError):
        strat.zscore_mean_reversion_signals(pd.Series([1.0, 2.0, 3.0]), 20, 1.0, 1.5)


def test_rsi2_requires_uptrend_and_pullback() -> None:
    uptrend = list(100 + np.arange(220) * 0.5)
    pullback = [uptrend[-1] - 1.5 * i for i in range(1, 4)]
    signals = strat.rsi2_pullback_signals(pd.Series(uptrend + pullback), trend_window=200)

    assert signals.iloc[:200].eq(0.0).all()  # not enough history for the trend filter
    assert signals.iloc[-1] == 1.0  # oversold inside an uptrend

    downtrend = list(300 - np.arange(220) * 0.5)
    bounce = [downtrend[-1] - 1.5 * i for i in range(1, 4)]
    blocked = strat.rsi2_pullback_signals(pd.Series(downtrend + bounce), trend_window=200)
    assert blocked.eq(0.0).all()  # oversold but below the long-term average: no trade


def test_rsi_is_100_on_pure_gains_and_undefined_when_flat() -> None:
    rising = strat._rsi(pd.Series(np.arange(1.0, 30.0)), 2)
    flat = strat._rsi(pd.Series([5.0] * 30), 2)

    assert rising.iloc[-1] == 100.0
    assert flat.isna().all()


# ---------------------------------------------------------------- momentum
def _universe() -> pd.DataFrame:
    index = pd.bdate_range("2023-01-02", periods=300)
    return pd.DataFrame(
        {
            "WINNER": 100 * 1.002 ** np.arange(300),
            "MEH": 100 * 1.0005 ** np.arange(300),
            "LOSER": 100 * 0.998 ** np.arange(300),
            "SHORT_HISTORY": [np.nan] * 200 + list(np.linspace(50, 80, 100)),
        },
        index=index,
    )


def test_momentum_ranks_leaders_and_ignores_missing_history() -> None:
    scores = strat.momentum_scores(_universe(), lookback=252, skip=21)

    assert scores["WINNER"] > scores["MEH"] > 0 > scores["LOSER"]
    assert np.isnan(scores["SHORT_HISTORY"])


def test_top_momentum_weights_are_equal_and_cash_when_nothing_trends() -> None:
    weights = strat.top_momentum_weights(_universe(), top_n=2)

    assert weights["WINNER"] == weights["MEH"] == 0.5
    assert weights["LOSER"] == 0.0 and weights["SHORT_HISTORY"] == 0.0

    falling = _universe()[["LOSER"]]
    assert strat.top_momentum_weights(falling, top_n=3).sum() == 0.0


# ---------------------------------------------------------------- ensemble + sizing
def test_ensemble_needs_agreement() -> None:
    index = pd.RangeIndex(4)
    votes = {
        "a": pd.Series([1, 1, 0, -1], index=index),
        "b": pd.Series([1, 0, 0, -1], index=index),
        "c": pd.Series([1, 0, 1, -1], index=index),
    }

    combined = strat.ensemble_vote(votes, threshold=0.6)

    assert list(combined) == [1.0, 0.0, 0.0, -1.0]


def test_volatility_target_scales_down_when_markets_get_wild() -> None:
    rng = np.random.default_rng(3)
    calm = rng.normal(0, 0.004, 120)
    wild = rng.normal(0, 0.03, 120)
    prices = pd.Series(100 * np.exp(np.cumsum(np.concatenate([calm, wild]))))

    scale = strat.volatility_target_scale(prices, target_volatility=0.15, window=20)

    assert scale.iloc[:20].eq(0.0).all()
    assert scale.between(0.0, 1.0).all()
    assert scale.iloc[100:120].mean() > scale.iloc[200:240].mean()


# ---------------------------------------------------------------- validation
def test_missing_columns_and_bad_parameters_raise() -> None:
    with pytest.raises(ValueError, match="missing required columns"):
        strat.supertrend(pd.DataFrame({"Close": [1.0, 2.0]}))
    with pytest.raises(ValueError):
        strat.donchian_breakout_signals(_noisy_walk(50), entry_window=0)
    with pytest.raises(ValueError):
        strat.supertrend(_noisy_walk(50), multiplier=-1)
    with pytest.raises(ValueError):
        strat.momentum_scores(_universe(), lookback=10, skip=10)


# ---------------------------------------------------------------- causality (no look-ahead)
CAUSAL_CASES = {
    "supertrend": lambda f: strat.supertrend_signals(f, allow_short=True),
    "donchian": lambda f: strat.donchian_breakout_signals(f, allow_short=True),
    "zscore": lambda f: strat.zscore_mean_reversion_signals(f["Close"], allow_short=True),
    "rsi2": lambda f: strat.rsi2_pullback_signals(f["Close"], trend_window=50),
    "vol_target": lambda f: strat.volatility_target_scale(f["Close"]),
}


@pytest.mark.parametrize("name", CAUSAL_CASES)
def test_signals_do_not_change_when_future_bars_are_added(name: str) -> None:
    full = _noisy_walk(320)
    compute = CAUSAL_CASES[name]
    expected = compute(full)

    for cut in (90, 150, 233, 319):
        partial = compute(full.iloc[:cut])
        pd.testing.assert_series_equal(partial, expected.iloc[:cut], check_names=False)


# ---------------------------------------------------------------- end-to-end with the backtester
def test_signals_plug_into_the_existing_backtester() -> None:
    frame = _trend_then_reversal(200, 100)
    signals = strat.supertrend_signals(frame)

    data, metrics = run_backtest(frame["Close"], signals, initial_capital=100_000.0, cost_bps=5.0)

    assert metrics.trade_count >= 1
    assert metrics.total_return > 0  # rode the clean uptrend
    assert metrics.max_drawdown > -0.5
    assert data["position"].iloc[0] == 0.0  # signals apply from the next bar


def test_volatility_scaled_signal_is_a_valid_backtest_input() -> None:
    frame = _noisy_walk(300)
    scaled = strat.supertrend_signals(frame) * strat.volatility_target_scale(frame["Close"])

    _, metrics = run_backtest(frame["Close"], scaled, initial_capital=100_000.0, cost_bps=5.0)

    assert np.isfinite(metrics.total_return)
