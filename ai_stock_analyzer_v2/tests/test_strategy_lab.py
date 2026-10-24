"""Tests for the strategy lab glue (signals -> backtester)."""

import numpy as np
import pandas as pd
import pytest

from algorithmic_trading.strategy_lab import (
    STRATEGIES,
    build_signals,
    compare_strategies,
    normalise_price_frame,
    run_strategy_lab,
)


def _frame(n: int = 400, seed: int = 7, drift: float = 0.0004) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(drift, 0.012, n)))
    index = pd.bdate_range("2023-01-02", periods=n)
    spread = np.abs(rng.normal(0.004, 0.002, n)) * close
    return pd.DataFrame(
        {
            "Open": close,
            "High": close + spread,
            "Low": close - spread,
            "Close": close,
            "Volume": 1_000.0,
        },
        index=index,
    )


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_every_strategy_runs_and_signals_are_bounded(strategy: str) -> None:
    result = run_strategy_lab(_frame(), strategy, allow_short=True)

    assert set(result.signals.dropna().unique()) <= {-1.0, 0.0, 1.0}
    assert len(result.curve) == len(result.signals)
    assert np.isfinite(result.metrics.total_return)
    assert result.metrics.max_drawdown <= 0.0


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_long_only_never_goes_short(strategy: str) -> None:
    signals = build_signals(_frame(), strategy, allow_short=False)

    assert (signals >= 0).all()


CUTS = (120, 180, 233, 290, 347, 399)


def _lookahead_detected(signal_fn, frame: pd.DataFrame) -> bool:
    """True if signals on the full history differ from signals on a truncated history.

    A causal signal at bar t depends only on bars <= t, so computing it on data cut off at
    bar t must give the same value. Any dependence on future bars shows up as a mismatch
    at one of the cut points.
    """
    full = signal_fn(frame)
    for cut in CUTS:
        truncated = signal_fn(frame.iloc[:cut])
        if not np.array_equal(full.iloc[:cut].to_numpy(), truncated.to_numpy()):
            return True
    return False


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_signals_have_no_lookahead(strategy: str) -> None:
    assert not _lookahead_detected(lambda f: build_signals(f, strategy, allow_short=True), _frame())


def test_lookahead_check_catches_a_signal_that_peeks_ahead() -> None:
    # Guards the guard: a signal using tomorrow's close must be flagged.
    def cheating(frame: pd.DataFrame) -> pd.Series:
        return (frame["Close"].shift(-1) > frame["Close"]).astype(float)

    assert _lookahead_detected(cheating, _frame())


def test_volatility_targeting_never_increases_exposure() -> None:
    frame = _frame()
    raw = run_strategy_lab(frame, "Supertrend")
    scaled = run_strategy_lab(frame, "Supertrend", target_volatility=0.10, max_leverage=1.0)

    assert (scaled.signals.abs() <= raw.signals.abs() + 1e-12).all()
    assert scaled.metrics.volatility <= raw.metrics.volatility + 1e-9


def test_higher_costs_lower_returns() -> None:
    frame = _frame()
    cheap = run_strategy_lab(frame, "Donchian breakout", cost_bps=0.0)
    costly = run_strategy_lab(frame, "Donchian breakout", cost_bps=100.0)

    assert costly.metrics.total_return < cheap.metrics.total_return


def test_normalise_flattens_yfinance_multiindex() -> None:
    frame = _frame()
    frame.columns = pd.MultiIndex.from_product([frame.columns, ["RELIANCE.BO"]])

    clean = normalise_price_frame(frame)

    assert {"High", "Low", "Close"} <= set(clean.columns)
    assert not isinstance(clean.columns, pd.MultiIndex)


def test_normalise_drops_bad_rows_and_duplicates() -> None:
    frame = _frame(50)
    frame.iloc[3, frame.columns.get_loc("Close")] = np.nan
    frame.iloc[5, frame.columns.get_loc("Close")] = -1.0
    frame = pd.concat([frame, frame.iloc[[10]]])

    clean = normalise_price_frame(frame)

    assert clean.index.is_unique and clean.index.is_monotonic_increasing
    assert (clean["Close"] > 0).all()
    assert len(clean) == 48


@pytest.mark.parametrize("bad", [None, pd.DataFrame(), pd.DataFrame({"Close": [1.0]})])
def test_unusable_frames_raise_value_error(bad) -> None:
    with pytest.raises(ValueError):
        normalise_price_frame(bad)


def test_unknown_strategy_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown strategy"):
        build_signals(_frame(), "Astrology")


def test_compare_strategies_returns_one_row_each() -> None:
    table = compare_strategies(_frame())

    assert list(table["Strategy"]) == list(STRATEGIES)
    assert table["Max drawdown"].le(0).all()


def test_cost_model_replaces_the_flat_bps_cost() -> None:
    from algorithmic_trading.trading_costs import india_cost_model

    frame = _frame()
    flat_free = run_strategy_lab(frame, "Donchian breakout", cost_bps=0.0)
    flat_ignored = run_strategy_lab(
        frame, "Donchian breakout", cost_bps=500.0, cost_model=india_cost_model("delivery")
    )
    with_model = run_strategy_lab(
        frame, "Donchian breakout", cost_bps=0.0, cost_model=india_cost_model("delivery")
    )

    # the model's costs apply (returns drop) and the flat 500 bps is not also charged
    assert with_model.metrics.total_return < flat_free.metrics.total_return
    assert flat_ignored.metrics.total_return == pytest.approx(with_model.metrics.total_return)


def test_compare_strategies_accepts_a_cost_model() -> None:
    from algorithmic_trading.trading_costs import india_cost_model

    cheap = compare_strategies(_frame(), cost_bps=0.0)
    costly = compare_strategies(_frame(), cost_model=india_cost_model("delivery"))

    assert (costly["Total return"].to_numpy() <= cheap["Total return"].to_numpy() + 1e-12).all()
