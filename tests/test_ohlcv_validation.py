from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from services.ohlcv_validation import build_data_status, validate_ohlcv_frame


def _valid_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [10.0, 11.0],
            "High": [12.0, 13.0],
            "Low": [9.0, 10.0],
            "Close": [11.0, 12.0],
            "Volume": [100, 200],
        },
        index=pd.to_datetime(["2026-10-30 09:15", "2026-10-30 09:16"]),
    )


def test_valid_ohlcv_is_sorted_and_preserved() -> None:
    frame = _valid_frame().iloc[::-1]
    result, errors = validate_ohlcv_frame(frame)
    assert errors == []
    assert result.index.is_monotonic_increasing
    assert result["Close"].tolist() == [11.0, 12.0]


def test_missing_required_columns_are_rejected() -> None:
    result, errors = validate_ohlcv_frame(pd.DataFrame({"Close": [10.0]}))
    assert result.empty
    assert errors == ["missing columns: Open, High, Low, Volume"]


def test_invalid_ohlc_relationship_is_rejected() -> None:
    frame = _valid_frame()
    frame.loc[frame.index[0], "High"] = 8.0
    result, errors = validate_ohlcv_frame(frame)
    assert result.empty
    assert "invalid OHLC relationship" in errors


def test_negative_volume_and_nonpositive_prices_are_rejected() -> None:
    frame = _valid_frame()
    frame.loc[frame.index[0], "Volume"] = -1
    frame.loc[frame.index[1], "Close"] = 0
    result, errors = validate_ohlcv_frame(frame)
    assert result.empty
    assert "negative volume" in errors
    assert "nonpositive price" in errors


def test_duplicate_timestamps_are_rejected() -> None:
    frame = _valid_frame()
    frame.index = [frame.index[0], frame.index[0]]
    result, errors = validate_ohlcv_frame(frame)
    assert result.empty
    assert "duplicate timestamps" in errors


def test_data_status_reports_source_retrieval_and_last_bar() -> None:
    frame, errors = validate_ohlcv_frame(_valid_frame())
    retrieved = datetime(2026, 10, 30, 10, 0, tzinfo=timezone.utc)
    status = build_data_status(frame, source="Yahoo Finance", retrieved_at=retrieved, errors=errors)
    assert status["source"] == "Yahoo Finance"
    assert status["retrieved_at"] == retrieved.isoformat()
    assert status["last_bar"] == "2026-10-30T09:16:00"
    assert status["status"] == "VALID"
    assert status["row_count"] == 2
