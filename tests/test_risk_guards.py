import pandas as pd
import pytest

from algorithmic_trading.risk_guards import (
    GuardConfig,
    compare_guards,
    simulate_with_guards,
    sma_crossover_signal,
)

IDX = pd.bdate_range("2024-01-01", periods=60)


def _px(values):
    series = pd.Series(100.0, index=IDX)
    series.iloc[: len(values)] = values
    return series


def _always_on():
    return pd.Series(True, index=IDX)


def test_no_guards_holds_through_a_crash():
    path = [100] * 10 + [100 - i * 2 for i in range(1, 16)]  # falls to 70
    close = _px(path)
    res = simulate_with_guards(close, _always_on(), GuardConfig(cost_bps=0))
    assert res.exits_by_reason == {"still open": 1}
    assert res.max_drawdown == pytest.approx(-0.30, abs=0.01)


def test_stop_loss_exits_at_the_breach_and_does_not_reenter_while_signal_stays_on():
    close = _px([100] * 10 + [100 - i * 2 for i in range(1, 16)])
    res = simulate_with_guards(close, _always_on(), GuardConfig(stop_loss=0.10, cost_bps=0))
    assert res.exits_by_reason["stop-loss"] == 1
    assert len(res.trades) == 1  # blocked from re-entry
    # a stop fills at the next close, so it can overshoot by one step but not run to -30%
    assert -0.13 < res.max_drawdown <= -0.10


def test_take_profit_and_trailing_stop_fire():
    up_then_down = [100, 100, 110, 120, 130, 120, 110, 100] + [100] * 52
    take = simulate_with_guards(
        _px(up_then_down), _always_on(), GuardConfig(take_profit=0.15, cost_bps=0)
    )
    assert take.exits_by_reason.get("take-profit") == 1
    trail = simulate_with_guards(
        _px(up_then_down), _always_on(), GuardConfig(trailing_stop=0.08, cost_bps=0)
    )
    assert trail.exits_by_reason.get("trailing stop") == 1
    assert trail.trades["return"].iloc[0] == pytest.approx(0.10)  # exits at 110, not back at 100


def test_kill_switch_halts_everything_after_the_limit():
    zigzag = [100, 90, 100, 90, 100, 90, 100, 90] * 7
    signal = pd.Series([i % 2 == 0 for i in range(60)], index=IDX)
    killed = simulate_with_guards(
        _px(zigzag), signal, GuardConfig(kill_switch_drawdown=0.05, cost_bps=0)
    )
    assert killed.killed_on is not None
    after = killed.equity.loc[killed.killed_on :]
    assert after.nunique() == 1  # flat once halted


def test_costs_reduce_equity():
    close = _px(list(range(100, 130)))
    free = simulate_with_guards(close, _always_on(), GuardConfig(cost_bps=0))
    paid = simulate_with_guards(close, _always_on(), GuardConfig(cost_bps=50))
    assert paid.total_return < free.total_return


def test_compare_and_signal_helpers():
    close = pd.Series(range(100, 200), index=pd.bdate_range("2024-01-01", periods=100), dtype=float)
    plain, guarded = compare_guards(
        close, sma_crossover_signal(close, 5, 20), GuardConfig(stop_loss=0.2)
    )
    assert plain.total_return == pytest.approx(guarded.total_return)  # a steady uptrend never stops
    with pytest.raises(ValueError):
        sma_crossover_signal(close, 20, 5)


@pytest.mark.parametrize("bad", [{"stop_loss": 0}, {"take_profit": 1.5}, {"cost_bps": -1}])
def test_invalid_config_rejected(bad):
    with pytest.raises(ValueError):
        simulate_with_guards(_px([100] * 40), _always_on(), GuardConfig(**bad))
