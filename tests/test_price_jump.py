import pandas as pd

from scanner.price_jump import _candle_settings, calculate_price_jump


def test_calculate_price_jump_uses_same_session_bars():
    index = pd.to_datetime(
        [
            "2026-09-17 15:25",
            "2026-09-18 09:15",
            "2026-09-18 09:20",
        ]
    )
    frame = pd.DataFrame(
        {
            "Close": [100.0, 100.0, 101.5],
            "Volume": [1000, 1200, 1800],
        },
        index=index,
    )

    result = calculate_price_jump(frame, lookback_bars=1, jump_percent=1.0)

    assert result is not None
    assert result["intraday_pct"] == 1.5
    assert result["day_pct"] == 1.5
    assert result["qualifies"] == 1.0
    assert result["volume"] == 1800.0


def test_calculate_price_jump_rejects_insufficient_bars():
    frame = pd.DataFrame(
        {
            "Close": [100.0],
            "Volume": [1000],
        },
        index=pd.to_datetime(["2026-09-18 09:15"]),
    )

    assert calculate_price_jump(frame, lookback_bars=1) is None


def test_calculate_price_jump_does_not_cross_session_boundary():
    index = pd.to_datetime(["2026-09-17 15:25", "2026-09-18 09:15"])
    frame = pd.DataFrame(
        {
            "Close": [100.0, 105.0],
            "Volume": [1000, 2000],
        },
        index=index,
    )

    assert calculate_price_jump(frame, lookback_bars=1) is None


def test_calculate_price_jump_supports_short_window_bar_count():
    index = pd.date_range("2026-09-18 09:15", periods=4, freq="1min")
    frame = pd.DataFrame(
        {
            "Close": [100.0, 100.2, 100.5, 101.5],
            "Volume": [1000, 1100, 1200, 2000],
        },
        index=index,
    )

    result = calculate_price_jump(frame, lookback_bars=3, jump_percent=1.0)

    assert result is not None
    assert round(result["intraday_pct"], 2) == 1.5
    assert result["qualifies"] == 1.0


def test_calculate_price_jump_supports_one_minute_window():
    index = pd.date_range("2026-09-18 09:15", periods=2, freq="1min")
    frame = pd.DataFrame(
        {
            "Close": [100.0, 101.0],
            "Volume": [1000, 1800],
        },
        index=index,
    )

    result = calculate_price_jump(frame, lookback_bars=1, jump_percent=0.5)

    assert result is not None
    assert result["intraday_pct"] == 1.0
    assert result["day_pct"] == 1.0
    assert result["qualifies"] == 1.0


def test_candle_settings_use_one_minute_for_short_windows():
    assert _candle_settings(1) == ("1m", 1)
    assert _candle_settings(2) == ("1m", 2)
    assert _candle_settings(3) == ("1m", 3)


def test_candle_settings_use_five_minute_for_longer_windows():
    assert _candle_settings(5) == ("5m", 1)
    assert _candle_settings(10) == ("5m", 2)
