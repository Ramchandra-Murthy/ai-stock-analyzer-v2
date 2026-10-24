import pandas as pd
import pytest

from ai_trading.point_in_time import point_in_time_slice, validate_timestamp_column


def test_validate_timestamp_column_accepts_sorted_timestamps():
    frame = pd.DataFrame(
        {
            "timestamp": ["2026-01-01", "2026-01-02", "2026-01-03"],
            "close": [100, 101, 102],
        }
    )

    result = validate_timestamp_column(frame, timestamp_column="timestamp")

    assert result.tolist() == [
        pd.Timestamp("2026-01-01"),
        pd.Timestamp("2026-01-02"),
        pd.Timestamp("2026-01-03"),
    ]


def test_validate_timestamp_column_rejects_unsorted_data():
    frame = pd.DataFrame(
        {
            "timestamp": ["2026-01-02", "2026-01-01"],
            "close": [101, 100],
        }
    )

    with pytest.raises(ValueError, match="sorted"):
        validate_timestamp_column(frame, timestamp_column="timestamp")


def test_validate_timestamp_column_rejects_invalid_values():
    frame = pd.DataFrame({"timestamp": ["2026-01-01", "not-a-date"]})

    with pytest.raises(ValueError, match="invalid or missing"):
        validate_timestamp_column(frame, timestamp_column="timestamp")


def test_point_in_time_slice_excludes_future_observations():
    frame = pd.DataFrame(
        {
            "timestamp": [
                "2026-01-01 09:15",
                "2026-01-01 09:20",
                "2026-01-01 09:25",
            ],
            "close": [100, 101, 102],
        }
    )

    result = point_in_time_slice(
        frame,
        timestamp_column="timestamp",
        as_of="2026-01-01 09:20",
    )

    assert result["close"].tolist() == [100, 101]


def test_point_in_time_slice_preserves_original_frame():
    frame = pd.DataFrame(
        {
            "timestamp": ["2026-01-01", "2026-01-02"],
            "close": [100, 101],
        }
    )

    result = point_in_time_slice(
        frame,
        timestamp_column="timestamp",
        as_of="2026-01-01",
    )

    assert len(frame) == 2
    assert len(result) == 1


def test_point_in_time_slice_requires_timestamp_column():
    frame = pd.DataFrame({"close": [100, 101]})

    with pytest.raises(KeyError, match="missing timestamp column"):
        point_in_time_slice(
            frame,
            timestamp_column="timestamp",
            as_of="2026-01-01",
        )
