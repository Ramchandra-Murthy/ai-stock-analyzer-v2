"""Tests for walk-forward parameter optimisation."""

import numpy as np
import pandas as pd
import pytest

from algorithmic_trading import walk_forward_optimizer as wf


def _ohlc(n: int = 900, seed: int = 3) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0.0004, 0.012, n)))
    index = pd.bdate_range("2019-01-01", periods=n)
    return pd.DataFrame(
        {
            "Open": close,
            "High": close * 1.006,
            "Low": close * 0.994,
            "Close": close,
            "Volume": 1_000_000,
        },
        index=index,
    )


def test_windows_are_ordered_non_overlapping_in_test_and_train_precedes_test() -> None:
    windows = wf.make_windows(1000, train_bars=300, test_bars=100)

    assert windows[0][2] == 300
    for (a, b, c, d), nxt in zip(windows, windows[1:] + [None], strict=True):
        assert a < b == c < d
        assert b - a == 300 and d - c == 100
        if nxt is not None:
            assert nxt[2] == d  # test slices tile with no gap and no overlap
    assert windows[-1][3] <= 1000


def test_anchored_windows_grow_from_the_start() -> None:
    windows = wf.make_windows(600, 200, 100, anchored=True)

    assert all(w[0] == 0 for w in windows)
    assert [w[1] - w[0] for w in windows] == [200, 300, 400, 500]


def test_window_arguments_are_validated() -> None:
    with pytest.raises(ValueError):
        wf.make_windows(500, 10, 50)
    with pytest.raises(ValueError):
        wf.make_windows(500, 100, 1)


def test_not_enough_history_raises() -> None:
    with pytest.raises(ValueError, match="Not enough history"):
        wf.walk_forward_optimize(_ohlc(300), "Supertrend", train_bars=504, test_bars=126)


def test_unknown_strategy_raises() -> None:
    with pytest.raises(ValueError):
        wf.parameter_combinations("Magic")


def test_donchian_grid_only_has_exit_shorter_than_entry() -> None:
    combos = wf.parameter_combinations("Donchian breakout")

    assert combos and all(c["dc_exit"] < c["dc_entry"] for c in combos)


def test_sharpe_matches_hand_calculation_and_handles_flat_series() -> None:
    r = pd.Series([0.01, -0.005, 0.02, 0.0, 0.004])
    expected = r.mean() / r.std(ddof=1) * np.sqrt(252)

    assert wf.sharpe(r) == pytest.approx(expected)
    assert wf.sharpe(pd.Series([0.0] * 10)) == 0.0
    assert wf.sharpe(pd.Series([0.01])) == 0.0


def test_returns_summary_hand_computed() -> None:
    idx = pd.date_range("2024-01-01", periods=3, freq="D")
    s = wf.returns_summary(pd.Series([0.10, -0.10, 0.10], index=idx))

    assert s["total_return"] == pytest.approx(1.1 * 0.9 * 1.1 - 1)
    assert s["max_drawdown"] == pytest.approx(-0.10)


# ---- selection logic with crafted returns -------------------------------------------------
def _crafted(n: int = 400):
    """Parameter set A is great in the first half and awful afterwards; B is the reverse."""
    index = pd.bdate_range("2020-01-01", periods=n)
    rng = np.random.default_rng(0)
    noise = rng.normal(0, 0.002, n)
    a = pd.Series(noise + np.where(np.arange(n) < n // 2, 0.003, -0.003), index=index)
    b = pd.Series(noise + np.where(np.arange(n) < n // 2, -0.003, 0.003), index=index)
    toggling = pd.Series(np.tile([0.0, 1.0], n // 2), index=index)  # trades every bar
    keys = {"A": (("p", 1.0),), "B": (("p", 2.0),)}
    returns = {keys["A"]: a, keys["B"]: b}
    positions = {keys["A"]: toggling, keys["B"]: toggling}
    market = pd.Series(0.0005, index=index)
    return returns, positions, market, keys


def test_choice_uses_only_the_train_slice() -> None:
    returns, positions, market, keys = _crafted()
    windows = [(0, 100, 100, 150), (200, 300, 300, 350)]

    result = wf.select_and_evaluate(returns, positions, market, windows)

    # window 1 trains on the first half where A shines, window 2 on the second half where B does
    assert "p=1" in result.windows.loc[0, "chosen_parameters"]
    assert "p=2" in result.windows.loc[1, "chosen_parameters"]
    # and the chosen set is then scored on data it never trained on
    assert result.windows.loc[0, "test_start"] == returns[keys["A"]].index[100]


def test_oos_returns_are_exactly_the_chosen_sets_test_slices() -> None:
    returns, positions, market, keys = _crafted()
    windows = [(0, 100, 100, 150), (200, 300, 300, 350)]

    result = wf.select_and_evaluate(returns, positions, market, windows)

    expected = pd.concat([returns[keys["A"]].iloc[100:150], returns[keys["B"]].iloc[300:350]])
    pd.testing.assert_series_equal(result.oos_returns, expected, check_names=False)
    assert len(result.buy_hold_returns) == len(result.oos_returns)


def test_strategies_that_barely_trade_are_not_selected() -> None:
    returns, positions, market, keys = _crafted()
    still = pd.Series(0.0, index=market.index)  # never trades
    positions = {keys["A"]: still, keys["B"]: still}

    result = wf.select_and_evaluate(returns, positions, market, [(0, 100, 100, 150)])

    assert result.windows.loc[0, "chosen_parameters"].startswith("flat")
    assert result.oos["total_return"] == 0.0


def test_no_windows_raises() -> None:
    returns, positions, market, _ = _crafted()
    with pytest.raises(ValueError):
        wf.select_and_evaluate(returns, positions, market, [])


# ---- end to end -----------------------------------------------------------------------------
def test_chosen_parameters_do_not_depend_on_data_after_the_test_window_starts() -> None:
    """The look-ahead check: rewrite the future and the earlier choices must not move."""
    frame = _ohlc(900)
    base = wf.walk_forward_optimize(frame, "Supertrend", train_bars=300, test_bars=100)

    altered = frame.copy()
    cut = 600
    rng = np.random.default_rng(99)
    shock = np.exp(np.cumsum(rng.normal(0, 0.03, len(frame) - cut)))
    for col in ("Open", "High", "Low", "Close"):
        altered.iloc[cut:, altered.columns.get_loc(col)] = altered[col].iloc[cut - 1] * shock
    changed = wf.walk_forward_optimize(altered, "Supertrend", train_bars=300, test_bars=100)

    # windows whose train and test slices end at or before the cut are untouched
    safe = base.windows[base.windows["test_end"] < frame.index[cut]]
    assert len(safe) >= 2
    pd.testing.assert_frame_equal(safe, changed.windows.iloc[: len(safe)])
    pd.testing.assert_series_equal(
        base.oos_returns.loc[: safe["test_end"].iloc[-1]],
        changed.oos_returns.loc[: safe["test_end"].iloc[-1]],
    )


@pytest.mark.parametrize("strategy", list(wf.PARAM_GRIDS))
def test_every_strategy_runs_end_to_end(strategy: str) -> None:
    result = wf.walk_forward_optimize(_ohlc(800), strategy, train_bars=300, test_bars=100)

    assert len(result.windows) == 5
    assert set(result.oos) == {"total_return", "cagr", "sharpe", "max_drawdown"}
    assert 0.0 <= result.parameter_stability <= 1.0
    assert result.oos_returns.index.is_monotonic_increasing
    assert result.oos_returns.index.is_unique


def test_cost_model_lowers_out_of_sample_result() -> None:
    from algorithmic_trading.trading_costs import india_cost_model

    frame = _ohlc(800)
    free = wf.walk_forward_optimize(frame, "Z-score mean reversion", cost_bps=0.0, train_bars=300)
    costly = wf.walk_forward_optimize(
        frame,
        "Z-score mean reversion",
        train_bars=300,
        cost_model=india_cost_model("delivery", slippage_bps=20.0),
    )

    assert costly.oos["total_return"] <= free.oos["total_return"] + 1e-12


# ---- parameter surface ----------------------------------------------------------------------
def test_surface_shape_labels_and_validation() -> None:
    surface = wf.parameter_surface(_ohlc(600), "Supertrend", "st_period", "st_multiplier")

    assert surface.shape == (4, 4)
    assert surface.index.name == "st_multiplier" and surface.columns.name == "st_period"
    assert surface.notna().all().all()
    with pytest.raises(ValueError):
        wf.parameter_surface(_ohlc(600), "Supertrend", "st_period", "st_period")
    with pytest.raises(ValueError):
        wf.parameter_surface(_ohlc(600), "Supertrend", "st_period", "nonsense")


def test_surface_cell_equals_a_direct_run() -> None:
    from algorithmic_trading.strategy_lab import run_strategy_lab

    frame = _ohlc(600)
    surface = wf.parameter_surface(frame, "Supertrend", "st_period", "st_multiplier")
    direct = run_strategy_lab(
        frame, "Supertrend", cost_bps=10.0, params={"st_period": 14, "st_multiplier": 2.5}
    )

    assert surface.loc[2.5, 14] == pytest.approx(wf.sharpe(direct.curve["strategy_return"]))


def test_donchian_invalid_cells_are_nan() -> None:
    surface = wf.parameter_surface(_ohlc(600), "Donchian breakout", "dc_entry", "dc_exit")

    assert np.isnan(surface.loc[20, 20]) and np.isnan(surface.loc[10, 10])
    assert not np.isnan(surface.loc[5, 55])


def test_surface_robustness_numbers() -> None:
    surface = pd.DataFrame([[1.0, -1.0], [2.0, np.nan]])

    out = wf.surface_robustness(surface)

    assert out["share_positive"] == pytest.approx(2 / 3)
    assert out["best"] == 2.0 and out["median"] == 1.0
    assert wf.surface_robustness(pd.DataFrame([[np.nan]]))["best"] == 0.0


def test_selection_ignores_the_test_slice_even_when_it_disagrees_with_train() -> None:
    """A rule that peeks at the test slice would pick B here; the honest rule picks A."""
    returns, positions, market, keys = _crafted()
    # train on the first half (A is best), test in the second half (B is best)
    result = wf.select_and_evaluate(returns, positions, market, [(0, 100, 250, 300)])

    assert "p=1" in result.windows.loc[0, "chosen_parameters"]
    assert result.windows.loc[0, "test_return"] < 0  # and it honestly reports the loss
