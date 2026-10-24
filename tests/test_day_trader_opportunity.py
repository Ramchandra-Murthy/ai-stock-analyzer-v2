import pandas as pd

from scanner.day_trader_opportunity import (
    _candle_settings,
    score_opportunity_rows,
    select_day_trader_universe,
    summarize_day_trading_setup,
)


def test_score_ranks_volume_momentum_breakout():
    rows = pd.DataFrame(
        [
            {
                "Symbol": "A",
                "5-min change %": 2.0,
                "Volume surge x": 3.0,
                "Session range %": 4.0,
                "Breakout": "YES",
                "Low-price flag": "YES",
            },
            {
                "Symbol": "B",
                "5-min change %": 0.5,
                "Volume surge x": 1.2,
                "Session range %": 1.0,
                "Breakout": "—",
                "Low-price flag": "—",
            },
        ]
    )

    result = score_opportunity_rows(rows)

    assert result.iloc[0]["Symbol"] == "A"
    assert result.iloc[0]["Opportunity score"] == 100.0
    assert result.iloc[0]["Setup"] == "Low-price volume watch"


def test_score_handles_empty_input():
    result = score_opportunity_rows(pd.DataFrame())

    assert result.empty


def test_safety_filter_removes_known_flags_only():
    from scanner.surveillance import apply_safety_filter

    candidates = pd.DataFrame(
        [
            {"Symbol": "SAFE", "Exchange": "NSE"},
            {"Symbol": "FLAGGED", "Exchange": "NSE"},
            {"Symbol": "BSE1", "Exchange": "BSE"},
        ]
    )
    safety = pd.DataFrame(
        [
            {
                "Symbol": "SAFE",
                "Safety flags": "",
                "Safety status": "NSE check clear",
            },
            {
                "Symbol": "FLAGGED",
                "Safety flags": "ASM: 11",
                "Safety status": "Flagged - review before trading",
            },
        ]
    )

    result = apply_safety_filter(candidates, safety, exclude_flagged=True)

    assert result["Symbol"].tolist() == ["SAFE", "BSE1"]
    assert result.loc[result["Symbol"].eq("BSE1"), "Safety status"].iloc[0] == (
        "Manual check required"
    )


def test_liquidity_warning():
    from scanner.surveillance import liquidity_warning

    assert liquidity_warning(4.0, 200_000) == "Low recent traded value"
    assert liquidity_warning(10.0, 100_000) == "Low recent traded value"
    assert liquidity_warning(20.0, 100_000) == "OK"


def test_universe_filters_exchange_and_cap_basket():
    large_nse = select_day_trader_universe("Large cap", "NSE")
    assert large_nse
    assert all(exchange == "NSE" for _, exchange in large_nse)
    assert "RELIANCE" in {symbol for symbol, _ in large_nse}
    assert "IRFC" not in {symbol for symbol, _ in large_nse}

    mid_both = select_day_trader_universe("Mid cap", "Both")
    assert mid_both
    assert {exchange for _, exchange in mid_both} == {"NSE", "BSE"}
    assert "IRFC" in {symbol for symbol, exchange in mid_both if exchange == "NSE"}


def test_universe_rejects_unknown_filters():
    assert select_day_trader_universe("Unknown cap", "Both") == []


def test_candle_settings_use_five_minute_for_default_scan():
    assert _candle_settings(5) == ("5m", 1)


def test_candle_settings_keep_fine_windows_on_one_minute_data():
    assert _candle_settings(2) == ("1m", 2)
    assert _candle_settings(3) == ("1m", 3)


def test_all_caps_uses_bounded_fast_universe():
    universe = select_day_trader_universe("All caps", "Both")
    assert universe
    assert len(universe) <= 200
    assert ("RELIANCE", "NSE") in universe


def test_score_combines_opportunity_and_setup_scores():
    rows = pd.DataFrame(
        [
            {
                "Symbol": "SETUP",
                "5-min change %": 2.0,
                "Volume surge x": 2.0,
                "Session range %": 2.0,
                "Breakout": "YES",
                "Low-price flag": "—",
                "Setup score": 80,
            }
        ]
    )

    result = score_opportunity_rows(rows)

    assert result.iloc[0]["Opportunity score"] == 75.0
    assert result.iloc[0]["Composite score"] == 77.0


def test_setup_evidence_reports_direction_and_confirmations():
    result = summarize_day_trading_setup(
        {
            "Long setup score": 80,
            "Short setup score": 35,
            "Trend": "UPTREND",
            "VWAP relation": "ABOVE",
            "EMA 9/20": "BULLISH",
            "RVOL": 2.1,
            "Breakout": "YES",
            "Breakdown": "NO",
        }
    )

    assert result["Direction"] == "LONG"
    assert result["Setup state"] == "LONG SETUP WATCH"
    assert "UPTREND" in result["Evidence"]
    assert "VWAP ABOVE" in result["Evidence"]
    assert "EMA BULLISH" in result["Evidence"]
    assert "RVOL CONFIRMED" in result["Evidence"]
    assert "BREAKOUT" in result["Evidence"]


def test_setup_evidence_marks_weak_context():
    result = summarize_day_trading_setup(
        {
            "Long setup score": 45,
            "Short setup score": 40,
            "Trend": "MIXED",
            "VWAP relation": "ABOVE",
            "EMA 9/20": "BULLISH",
            "RVOL": 0.9,
            "Breakout": "NO",
            "Breakdown": "NO",
        }
    )

    assert result["Direction"] == "LONG"
    assert result["Setup state"] == "CONTEXT ONLY"
    assert "No strong confirmation" not in result["Evidence"]


def test_day_trade_plan_long_references():
    from scanner.day_trading_strategy import calculate_day_trade_plan

    result = calculate_day_trade_plan(
        {
            "Long setup score": 80,
            "Short setup score": 30,
            "Close": 100.0,
            "ATR 14": 2.0,
            "Support": 98.0,
            "Resistance": 101.0,
        }
    )

    assert result["Plan"] == "LONG reference plan"
    assert result["Entry reference"] == 101.0
    assert result["Stop reference"] == 98.0
    assert result["Target 1"] == 104.0
    assert result["Target 2"] == 107.0
    assert result["Target 3"] == 110.0
    assert result["R:R T1"] == 1.0
    assert result["R:R T3"] == 3.0


def test_day_trade_plan_short_references():
    from scanner.day_trading_strategy import calculate_day_trade_plan

    result = calculate_day_trade_plan(
        {
            "Long setup score": 30,
            "Short setup score": 80,
            "Close": 100.0,
            "ATR 14": 2.0,
            "Support": 99.0,
            "Resistance": 102.0,
        }
    )

    assert result["Plan"] == "SHORT reference plan"
    assert result["Entry reference"] == 99.0
    assert result["Stop reference"] == 102.0
    assert result["Target 1"] == 96.0
    assert result["Target 3"] == 90.0


def test_day_trade_plan_rejects_neutral_direction():
    from scanner.day_trading_strategy import calculate_day_trade_plan

    result = calculate_day_trade_plan(
        {
            "Long setup score": 50,
            "Short setup score": 50,
            "Close": 100.0,
            "ATR 14": 2.0,
            "Support": 98.0,
            "Resistance": 102.0,
        }
    )

    assert result["Plan"] == "NO CLEAR DIRECTION"
    assert result["Entry reference"] is None


def test_day_trade_plan_state_waiting_long():
    from scanner.day_trading_strategy import classify_day_trade_plan_state

    state = classify_day_trade_plan_state(
        {"Close": 100.0},
        {
            "Plan": "LONG reference plan",
            "Entry reference": 101.0,
            "Stop reference": 98.0,
        },
    )
    assert state == "WAITING FOR REFERENCE"


def test_day_trade_plan_state_triggered_short():
    from scanner.day_trading_strategy import classify_day_trade_plan_state

    state = classify_day_trade_plan_state(
        {"Close": 98.0},
        {
            "Plan": "SHORT reference plan",
            "Entry reference": 99.0,
            "Stop reference": 102.0,
        },
    )
    assert state == "TRIGGERED / BELOW REFERENCE"


def test_day_trade_plan_state_invalidated():
    from scanner.day_trading_strategy import classify_day_trade_plan_state

    state = classify_day_trade_plan_state(
        {"Close": 97.0},
        {
            "Plan": "LONG reference plan",
            "Entry reference": 101.0,
            "Stop reference": 98.0,
        },
    )
    assert state == "INVALIDATED"
