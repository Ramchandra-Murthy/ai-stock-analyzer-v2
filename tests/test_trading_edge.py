import numpy as np
import pandas as pd
import pytest

from engine.trading_edge import (
    arithmetic_expectancy,
    geometric_expectancy,
    kelly_fraction,
    mean_reversion_signal,
    pair_zscore,
    pairs_trading_signal,
    trade_statistics,
    trend_following_signal,
)


def test_expectancy_formulas_match_chapter5_definitions():
    assert arithmetic_expectancy(0.4, 0.08, -0.03) == pytest.approx(0.014)
    assert geometric_expectancy(0.4, 0.08, -0.03) == pytest.approx((1.08**0.4) * (0.97**0.6) - 1)
    assert kelly_fraction(0.4, 0.08, -0.03) == pytest.approx(0.4 / 0.03 - 0.6 / 0.08)


def test_trade_statistics_calculates_edge_inputs():
    returns = pd.Series([0.10, -0.04, 0.06, -0.02, 0.03])
    result = trade_statistics(returns)

    assert result["trades"] == 5
    assert result["win_rate"] == pytest.approx(0.6)
    assert result["average_win"] == pytest.approx(0.0633333333)
    assert result["average_loss"] == pytest.approx(-0.03)
    assert result["arithmetic_expectancy"] > 0


def test_trend_following_signal_uses_fast_and_slow_average():
    close = pd.Series(np.arange(1.0, 81.0))
    result = trend_following_signal(close, fast_period=5, slow_period=20)

    assert result.iloc[:19].isna().all()
    assert result.iloc[-1] == 1


def test_mean_reversion_signal_flags_large_deviations():
    close = pd.Series([100.0] * 20 + [130.0])
    result = mean_reversion_signal(close, window=20, entry_z=2.0, exit_z=0.5)

    assert result.iloc[-1] == -1


def test_pair_zscore_and_pair_signal():
    first = pd.Series(np.arange(1.0, 81.0))
    second = pd.Series(np.arange(1.0, 81.0) * 0.9)
    zscore = pair_zscore(first, second, window=20)

    assert zscore.iloc[:19].isna().all()
    assert zscore.iloc[-1] == pytest.approx(0.0)

    custom = pd.Series([-2.5, 0.0, 2.5])
    signal = pairs_trading_signal(custom, entry_z=2.0, exit_z=0.5)
    assert signal.tolist() == [1.0, 0.0, -1.0]


def test_invalid_edge_parameters_raise():
    with pytest.raises(ValueError):
        arithmetic_expectancy(1.1, 0.1, -0.05)
    with pytest.raises(ValueError):
        kelly_fraction(0.5, 0.0, -0.05)
    with pytest.raises(ValueError):
        mean_reversion_signal(pd.Series([1.0, 2.0]), entry_z=0.5, exit_z=0.5)
