"""Tests for causal regime gates and their use in the Strategy Lab."""

import numpy as np
import pandas as pd
import pytest

from algorithmic_trading import regime_filter as rf
from algorithmic_trading.strategy_lab import run_strategy_lab


def _close(n: int = 700, seed: int = 5) -> pd.Series:
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2020-01-01", periods=n)
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.011, n))), index=idx)


def _frame(close: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {"Open": close, "High": close * 1.005, "Low": close * 0.995, "Close": close}
    )


def test_trend_gate_on_a_steady_uptrend_and_downtrend() -> None:
    idx = pd.bdate_range("2021-01-01", periods=300)
    up = pd.Series(np.linspace(100, 200, 300), index=idx)
    down = pd.Series(np.linspace(200, 100, 300), index=idx)

    assert not rf.trend_gate(up).iloc[:199].any()  # not enough history to call the trend
    assert rf.trend_gate(up).iloc[199:].all()
    assert not rf.trend_gate(down).any()


def test_trend_gate_hand_checked_small_case() -> None:
    close = pd.Series([1.0, 2.0, 3.0, 4.0, 2.0, 1.0])
    gate = rf.trend_gate(close, fast=2, slow=3)
    # slow MA: -,-,2,3,3,2.33 ; fast MA: -,1.5,2.5,3.5,3,1.5
    assert gate.tolist() == [False, False, True, True, False, False]


def test_invalid_arguments_raise() -> None:
    with pytest.raises(ValueError):
        rf.trend_gate(_close(), fast=50, slow=20)
    with pytest.raises(ValueError):
        rf.calm_volatility_gate(_close(), quantile=1.5)
    with pytest.raises(ValueError):
        rf.regime_gate(_close(), "nonsense")
    with pytest.raises(ValueError):
        rf.level_gate(_close())


def test_volatility_gate_turns_off_during_a_spike() -> None:
    rng = np.random.default_rng(1)
    returns = rng.normal(0, 0.005, 600)
    returns[500:530] = rng.normal(0, 0.05, 30)  # stress episode
    close = pd.Series(
        100 * np.exp(np.cumsum(returns)), index=pd.bdate_range("2020-01-01", periods=600)
    )

    gate = rf.calm_volatility_gate(close)

    assert gate.iloc[300:480].mean() > 0.7
    assert not gate.iloc[515:530].any()


@pytest.mark.parametrize("mode", rf.REGIME_MODES)
def test_gates_are_causal(mode: str) -> None:
    """The gate at bar t must not change when later data is removed or rewritten."""
    close = _close(700)
    full = rf.regime_gate(close, mode)
    for cut in (320, 450, 600):
        truncated = rf.regime_gate(close.iloc[:cut], mode)
        pd.testing.assert_series_equal(full.iloc[:cut], truncated)

    rewritten = close.copy()
    rewritten.iloc[500:] *= np.linspace(1, 3, 200)
    altered = rf.regime_gate(rewritten, mode)
    pd.testing.assert_series_equal(full.iloc[:500], altered.iloc[:500])


def test_apply_gate_flattens_and_treats_missing_as_off() -> None:
    idx = pd.date_range("2024-01-01", periods=5)
    signals = pd.Series([1.0, 1.0, -1.0, 1.0, 1.0], index=idx)
    gate = pd.Series([True, False, True], index=idx[:3])  # shorter than signals

    out = rf.apply_regime_gate(signals, gate)

    assert out.tolist() == [1.0, 0.0, -1.0, 0.0, 0.0]


def test_level_gate_bounds_and_missing() -> None:
    vix = pd.Series([12.0, 25.0, np.nan, 18.0])

    assert rf.level_gate(vix, below=20).tolist() == [True, False, False, True]
    assert rf.level_gate(vix, above=20).tolist() == [False, True, False, False]


def test_gated_strategy_holds_nothing_the_bar_after_gate_is_off() -> None:
    close = _close(700)
    frame = _frame(close)
    gate = rf.regime_gate(close, rf.REGIME_MODES[0])

    result = run_strategy_lab(frame, "Donchian breakout", regime=gate)

    # position on bar t+1 comes from the signal (and gate) on bar t
    held = result.curve["position"].ne(0)
    gate_prev = (
        gate.shift(1, fill_value=False).reindex(result.curve.index).fillna(False).astype(bool)
    )
    assert not (held & ~gate_prev).any()


def test_regime_none_matches_the_original_behaviour_and_always_on_gate_is_identical() -> None:
    close = _close(500)
    frame = _frame(close)

    plain = run_strategy_lab(frame, "Supertrend")
    always = run_strategy_lab(frame, "Supertrend", regime=pd.Series(True, index=close.index))

    pd.testing.assert_frame_equal(plain.curve, always.curve)
    assert rf.regime_share(pd.Series(True, index=close.index)) == 1.0


def test_gate_never_adds_exposure_beyond_the_ungated_strategy() -> None:
    close = _close(700)
    frame = _frame(close)
    gate = rf.regime_gate(close, rf.REGIME_MODES[2])

    plain = run_strategy_lab(frame, "Supertrend")
    gated = run_strategy_lab(frame, "Supertrend", regime=gate)

    assert gated.curve["position"].abs().sum() <= plain.curve["position"].abs().sum()
