import pandas as pd
import pytest

from scanner.short_regime import (
    floor_ceiling_regime,
    fractal_swings,
    higher_highs_lows,
    moving_average_regime,
    regime_breakdown,
    turtle_regime,
)


def test_fresh_high_is_bullish_after_lookback():
    frame = pd.DataFrame(
        {
            "High": [10, 11, 12, 13, 15],
            "Low": [8, 9, 10, 11, 12],
        }
    )

    result = regime_breakdown(frame, high_lookback=3, low_lookback=3)

    assert result.iloc[3] == "BULLISH"
    assert result.iloc[4] == "BULLISH"


def test_fresh_low_is_bearish_after_lookback():
    frame = pd.DataFrame(
        {
            "High": [15, 14, 13, 12, 11],
            "Low": [10, 9, 8, 7, 5],
        }
    )

    result = regime_breakdown(frame, high_lookback=3, low_lookback=3)

    assert result.iloc[3] == "BEARISH"
    assert result.iloc[4] == "BEARISH"


def test_current_bar_is_not_used_as_its_own_breakout_reference():
    frame = pd.DataFrame(
        {
            "High": [10, 11, 12, 12],
            "Low": [8, 9, 10, 10],
        }
    )

    result = regime_breakdown(frame, high_lookback=3, low_lookback=3)

    assert result.iloc[3] == "NEUTRAL"


def test_invalid_lookback_and_missing_columns_are_rejected():
    with pytest.raises(ValueError):
        regime_breakdown(pd.DataFrame({"High": [1], "Low": [1]}), high_lookback=0)

    with pytest.raises(ValueError):
        regime_breakdown(pd.DataFrame({"Close": [1]}), low_lookback=3)


def test_turtle_regime_requires_long_and_short_breakouts_to_agree():
    frame = pd.DataFrame(
        {
            "High": [15, 14, 13, 12, 11, 10],
            "Low": [10, 9, 8, 7, 6, 5],
        }
    )

    result = turtle_regime(frame, entry_lookback=4, exit_lookback=2)

    assert result.iloc[:4].tolist() == ["NEUTRAL"] * 4
    assert result.iloc[4] == "BEARISH"
    assert result.iloc[5] == "BEARISH"


def test_turtle_regime_stays_neutral_when_fast_regime_disagrees():
    frame = pd.DataFrame(
        {
            "High": [10, 11, 12, 13, 12],
            "Low": [8, 9, 10, 11, 10],
        }
    )

    result = turtle_regime(frame, entry_lookback=3, exit_lookback=2)

    assert result.iloc[3] == "BULLISH"
    assert result.iloc[4] == "NEUTRAL"


def test_turtle_regime_rejects_invalid_lookbacks():
    frame = pd.DataFrame({"High": [10, 11], "Low": [8, 9]})

    with pytest.raises(ValueError):
        turtle_regime(frame, entry_lookback=0)


def test_moving_average_regime_classifies_fast_above_and_below_slow():
    frame = pd.DataFrame({"Close": [1, 2, 3, 4, 3, 2]})
    result = moving_average_regime(frame, fast_window=2, slow_window=3)
    assert result.iloc[:2].tolist() == ["NEUTRAL", "NEUTRAL"]
    assert result.iloc[2] == "BULLISH"
    assert result.iloc[5] == "BEARISH"


def test_moving_average_regime_does_not_use_current_bar_in_its_window():
    frame = pd.DataFrame({"Close": [10, 10, 10, 20]})
    result = moving_average_regime(frame, fast_window=2, slow_window=3)
    assert result.iloc[2] == "NEUTRAL"
    assert result.iloc[3] == "BULLISH"


def test_moving_average_regime_rejects_invalid_windows_and_missing_price():
    frame = pd.DataFrame({"Close": [1, 2, 3]})
    with pytest.raises(ValueError):
        moving_average_regime(frame, fast_window=3, slow_window=3)
    with pytest.raises(ValueError):
        moving_average_regime(frame, fast_window=4, slow_window=3)
    with pytest.raises(ValueError):
        moving_average_regime(pd.DataFrame({"Open": [1, 2]}))


def test_fractal_swings_uses_hlc_average_and_finds_level_one_turns():
    frame = pd.DataFrame(
        {
            "High": [11, 15, 12, 14, 10],
            "Low": [9, 13, 10, 12, 8],
            "Close": [10, 14, 11, 13, 9],
        }
    )

    result = fractal_swings(frame, levels=1)

    assert result.loc[1, "Hi1"] == 14.0
    assert result.loc[2, "Lo1"] == 11.0
    assert result.loc[3, "Hi1"] == 13.0
    assert pd.isna(result.loc[0, "Hi1"])


def test_fractal_swings_builds_higher_levels_from_prior_swings():
    frame = pd.DataFrame(
        {
            "High": [11, 15, 12, 16, 13, 17, 14],
            "Low": [9, 13, 10, 14, 11, 15, 12],
            "Close": [10, 14, 11, 15, 12, 16, 13],
        }
    )

    result = fractal_swings(frame, levels=2)

    assert "Hi1" in result.columns
    assert "Lo1" in result.columns
    assert "Hi2" in result.columns
    assert "Lo2" in result.columns


def test_fractal_swings_rejects_invalid_levels_and_missing_columns():
    with pytest.raises(ValueError):
        fractal_swings(
            pd.DataFrame({"High": [1], "Low": [1], "Close": [1]}),
            levels=0,
        )

    with pytest.raises(ValueError):
        fractal_swings(pd.DataFrame({"High": [1], "Low": [1]}))


def test_higher_highs_lows_classifies_swing_progression():
    frame = pd.DataFrame(
        {
            "High": [10, 14, 11, 16, 12, 18, 13, 20, 14],
            "Low": [8, 12, 9, 13, 10, 14, 11, 15, 12],
            "Close": [9, 13, 10, 15, 11, 17, 12, 19, 13],
        }
    )

    result = higher_highs_lows(frame, levels=1, shift=1)

    assert "HH1" in result.columns
    assert "HL1" in result.columns
    assert "LH1" in result.columns
    assert "LL1" in result.columns
    assert result["HH1"].notna().any()
    assert result["HL1"].notna().any()


def test_higher_highs_lows_rejects_invalid_arguments():
    frame = pd.DataFrame(
        {
            "High": [10, 12, 11],
            "Low": [8, 10, 9],
            "Close": [9, 11, 10],
        }
    )

    with pytest.raises(ValueError):
        higher_highs_lows(frame, levels=0)

    with pytest.raises(ValueError):
        higher_highs_lows(frame, shift=0)

    with pytest.raises(ValueError):
        higher_highs_lows(pd.DataFrame({"High": [1], "Low": [1]}))


def test_floor_ceiling_regime_tracks_conservative_regime_changes():
    frame = pd.DataFrame(
        {
            "High": [10, 14, 11, 16, 12, 13, 10, 9, 8],
            "Low": [8, 12, 9, 13, 10, 11, 8, 7, 6],
            "Close": [9, 13, 10, 15, 11, 12, 9, 8, 7],
        }
    )

    result = floor_ceiling_regime(frame, levels=1)

    assert "Floor1" in result.columns
    assert "Ceiling1" in result.columns
    assert "HiLo_FC1" in result.columns
    assert result["Floor1"].notna().any()
    assert result["Ceiling1"].notna().any()
    assert set(result["HiLo_FC1"].dropna().unique()).issubset({"NEUTRAL", "BULLISH", "BEARISH"})


def test_floor_ceiling_regime_rejects_invalid_arguments():
    frame = pd.DataFrame(
        {
            "High": [10, 12, 11],
            "Low": [8, 10, 9],
            "Close": [9, 11, 10],
        }
    )

    with pytest.raises(ValueError):
        floor_ceiling_regime(frame, levels=0)

    with pytest.raises(ValueError):
        floor_ceiling_regime(pd.DataFrame({"High": [1], "Low": [1]}))
