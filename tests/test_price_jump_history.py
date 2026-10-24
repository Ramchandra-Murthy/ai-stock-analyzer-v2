import pandas as pd

from scanner.price_jump_history import append_price_jump_snapshot


def test_empty_snapshot_preserves_history():
    history = pd.DataFrame([{"Timestamp": "2026-09-18 09:20", "Symbol": "TCS", "Exchange": "NSE"}])
    result = append_price_jump_snapshot(history, pd.Timestamp("2026-09-18 09:25"), pd.DataFrame())
    pd.testing.assert_frame_equal(result, history)


def test_snapshot_keeps_price_jump_fields_and_deduplicates():
    jumps = pd.DataFrame(
        [
            {
                "Symbol": "TCS",
                "Exchange": "NSE",
                "Market-cap basket": "Large cap",
                "Last price": 3500.0,
                "Change over 5 min %": 1.25,
                "Latest bar volume": 50000,
                "Volume vs recent bars": 1.8,
                "Latest candle (provider time)": "2026-09-18 09:25",
            }
        ]
    )
    timestamp = pd.Timestamp("2026-09-18 09:25")
    first = append_price_jump_snapshot(None, timestamp, jumps)
    second = append_price_jump_snapshot(first, timestamp, jumps)

    assert len(second) == 1
    assert second.iloc[0]["Change over 5 min %"] == 1.25
    assert second.iloc[0]["Volume vs recent bars"] == 1.8


def test_snapshot_ignores_rows_without_numeric_change():
    jumps = pd.DataFrame(
        [
            {
                "Symbol": "INFY",
                "Exchange": "NSE",
                "Change over 5 min %": "not-a-number",
            }
        ]
    )
    result = append_price_jump_snapshot(None, pd.Timestamp("2026-09-18 09:30"), jumps)
    assert result.empty
