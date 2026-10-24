import numpy as np
import pandas as pd
import pytest

from engine.regime_engine import (
    chapter4_regime,
    classify_regime,
    composite_regime_score,
    latest_regime,
    multi_timeframe_regime,
    regime_breakout,
    regime_ema,
    regime_floor_ceiling,
    regime_fractal,
    regime_sma,
    regime_structure,
    relative_regime,
    turtle_trader,
)


def test_breakout_sets_and_carries_regime() -> None:
    frame = pd.DataFrame({"High": [10, 11, 12, 11, 10], "Low": [9, 8, 7, 8, 6]})
    result = regime_breakout(frame, periods=3)

    assert result.iloc[2] == 1
    assert result.iloc[3] == 1
    assert result.iloc[4] == -1


def test_sma_regime_uses_short_minus_long() -> None:
    frame = pd.DataFrame({"Close": [1, 2, 3, 4, 5, 4, 3]})
    result = regime_sma(frame, short_period=2, long_period=4)

    assert pd.isna(result.iloc[2])
    assert result.iloc[3] == 1
    assert result.iloc[-1] == -1


def test_ema_regime_uses_short_minus_long() -> None:
    frame = pd.DataFrame({"Close": [1, 2, 3, 4, 5, 4, 3]})
    result = regime_ema(frame, short_period=2, long_period=4)

    assert result.iloc[3] == 1
    assert result.iloc[-1] == -1


def test_turtle_returns_only_directional_or_neutral_states() -> None:
    frame = pd.DataFrame({"High": [10, 11, 12, 11, 10, 9], "Low": [9, 8, 7, 8, 9, 6]})
    result = turtle_trader(frame, entry_period=4, exit_period=2)

    assert set(result.unique()).issubset({-1, 0, 1})


def test_composite_regime_score_aligns_signals() -> None:
    first = pd.Series([1, 1, -1], name="a")
    second = pd.Series([1, -1, -1], name="b")

    result = composite_regime_score(first, second)

    assert result.tolist() == [2, 0, -2]


def test_breakout_rejects_invalid_period() -> None:
    frame = pd.DataFrame({"High": [1, 2], "Low": [0, 1]})

    with pytest.raises(ValueError):
        regime_breakout(frame, periods=1)


def _trend_frame(periods: int = 80, slope: float = 1.0) -> pd.DataFrame:
    close = 100 + np.arange(periods, dtype=float) * slope
    return pd.DataFrame(
        {
            "High": close + 0.5,
            "Low": close - 0.5,
            "Close": close,
        }
    )


def test_chapter4_uptrend_combines_directional_methods():
    result = chapter4_regime(
        _trend_frame(),
        breakout_period=10,
        turtle_entry_period=20,
        turtle_exit_period=10,
        ma_short_period=5,
        ma_long_period=10,
        fractal_window=2,
        structure_period=5,
        floor_ceiling_period=10,
    )
    latest = result.iloc[-1]
    assert latest["breakout"] == 1
    assert latest["turtle"] == 1
    assert latest["sma"] == 1
    assert latest["ema"] == 1
    assert latest["structure"] == 1
    assert latest["floor_ceiling"] == 1
    assert latest["regime_score"] >= 6
    assert latest["regime"] == "BULLISH"


def test_chapter4_downtrend_is_bearish():
    result = chapter4_regime(
        _trend_frame(slope=-1.0),
        breakout_period=10,
        turtle_entry_period=20,
        turtle_exit_period=10,
        ma_short_period=5,
        ma_long_period=10,
        fractal_window=2,
        structure_period=5,
        floor_ceiling_period=10,
    )
    latest = result.iloc[-1]
    assert latest["breakout"] == -1
    assert latest["turtle"] == -1
    assert latest["sma"] == -1
    assert latest["ema"] == -1
    assert latest["structure"] == -1
    assert latest["floor_ceiling"] == -1
    assert latest["regime_score"] <= -6
    assert latest["regime"] == "BEARISH"


def test_fractal_signal_is_confirmed_after_right_hand_bars():
    frame = pd.DataFrame(
        {
            "High": [10, 11, 12, 11, 10, 9, 8],
            "Low": [9, 8, 7, 8, 9, 7, 6],
            "Close": [9.5, 9.5, 9.5, 9.5, 9.5, 8.0, 7.0],
        }
    )
    result = regime_fractal(frame, window=2)
    assert result.iloc[4] == -1


def test_floor_ceiling_and_structure_have_directional_states():
    frame = _trend_frame(periods=20)
    floor_ceiling = regime_floor_ceiling(frame, periods=5)
    structure = regime_structure(frame, periods=3)
    assert floor_ceiling.iloc[-1] == 1
    assert structure.iloc[-1] == 1


def test_latest_and_multitimeframe_snapshots():
    frame = _trend_frame()
    snapshot = latest_regime(
        frame,
        breakout_period=10,
        turtle_entry_period=20,
        turtle_exit_period=10,
        ma_short_period=5,
        ma_long_period=10,
        floor_ceiling_period=10,
    )
    assert snapshot["regime"] == "BULLISH"

    result = multi_timeframe_regime(
        {"5m": frame, "daily": frame},
        weights={"5m": 1.0, "daily": 2.0},
        breakout_period=10,
        turtle_entry_period=20,
        turtle_exit_period=10,
        ma_short_period=5,
        ma_long_period=10,
        floor_ceiling_period=10,
    )
    assert list(result["Timeframe"]) == ["5m", "daily"]
    assert result.attrs["weighted_composite_score"] > 0


def test_relative_regime_follows_stock_strength_against_flat_benchmark():
    frame = _trend_frame()
    benchmark = pd.Series(100.0, index=frame.index)
    result = relative_regime(
        frame,
        benchmark,
        breakout_period=10,
        turtle_entry_period=20,
        turtle_exit_period=10,
        ma_short_period=5,
        ma_long_period=10,
        floor_ceiling_period=10,
    )
    assert result.iloc[-1]["regime"] == "BULLISH"


def test_classify_regime_buckets():
    assert classify_regime(4) == "BULLISH"
    assert classify_regime(-4) == "BEARISH"
    assert classify_regime(1) == "RANGE / MIXED"
    assert classify_regime(None) == "INSUFFICIENT DATA"
