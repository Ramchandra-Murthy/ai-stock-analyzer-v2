import pandas as pd

from scanner.day_trading_strategy import (
    analyze_day_trade_setup,
    prepare_day_trading_frame,
)


def _bars(closes, volumes=None):
    if volumes is None:
        volumes = [100] * len(closes)
    index = pd.date_range("2026-09-18 09:15", periods=len(closes), freq="5min")
    return pd.DataFrame(
        {
            "Open": [value - 0.2 for value in closes],
            "High": [value + 0.3 for value in closes],
            "Low": [value - 0.3 for value in closes],
            "Close": closes,
            "Volume": volumes,
        },
        index=index,
    )


def test_prepare_adds_core_day_trading_indicators():
    data = prepare_day_trading_frame(_bars([100, 101, 102, 103, 104, 105]))

    assert {"EMA 9", "EMA 20", "SMA 50", "ATR 14", "VWAP", "RVOL 20"}.issubset(data.columns)
    assert data["VWAP"].notna().all()


def test_analyzer_detects_breakout_with_volume_confirmation():
    closes = [100, 100.5, 101, 100.8, 101.2, 101.5, 102, 103, 104, 106]
    volumes = [100] * 9 + [300]
    result = analyze_day_trade_setup(
        _bars(closes, volumes),
        opening_range_bars=1,
        level_lookback=5,
    )

    assert result["Breakout"] == "YES"
    assert result["Volume confirmation"] == "YES"
    assert result["Trend"] == "UPTREND"
    assert result["Long setup score"] >= 70
    assert result["Setup"] == "LONG SETUP WATCH"


def test_analyzer_handles_mixed_conditions():
    result = analyze_day_trade_setup(
        _bars([100, 99.8, 100.1, 99.9, 100.0, 99.95]),
        opening_range_bars=1,
        level_lookback=3,
    )

    assert result["Setup"] in {"TREND WATCH", "NO CLEAR SETUP", "BREAKOUT/BREAKDOWN WATCH"}


def test_analyzer_rejects_insufficient_data():
    result = analyze_day_trade_setup(_bars([100, 101, 102]), opening_range_bars=1)

    assert result == {}
