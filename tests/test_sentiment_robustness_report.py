from datetime import UTC, datetime

import pandas as pd
import pytest

from ai_trading.sentiment_robustness_report import (
    load_news_records,
    load_price_bars,
    validate_coverage,
)


def test_load_news_records_normalizes_timezone_and_skips_invalid_rows():
    frame = pd.DataFrame(
        {
            "symbol": ["abc", "ABC"],
            "title": ["headline", "bad timestamp"],
            "source": ["wire", "wire"],
            "published_at": ["2026-10-01T09:00:00+05:30", "not-a-date"],
            "sentiment_score": [0.7, 0.2],
        }
    )
    records = load_news_records(frame)
    assert len(records) == 1
    assert records[0].symbol == "ABC"
    assert records[0].published_at == datetime(2026, 10, 1, 3, 30, tzinfo=UTC)


def test_load_news_records_requires_schema():
    with pytest.raises(ValueError, match="missing required columns"):
        load_news_records(pd.DataFrame({"title": ["headline"]}))


def test_load_price_bars_normalizes_and_checks_duplicate_timestamps():
    frame = pd.DataFrame(
        {
            "symbol": ["abc", "ABC"],
            "timestamp": ["2026-10-01T09:00:00Z", "2026-10-01T10:00:00Z"],
            "Close": ["100", "101"],
        }
    )
    bars = load_price_bars(frame)
    assert list(bars) == ["ABC"]
    assert bars["ABC"]["Close"].tolist() == [100.0, 101.0]

    duplicate = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="unique timestamps"):
        load_price_bars(duplicate)


def test_validate_coverage_counts_matching_symbols():
    records = load_news_records(
        pd.DataFrame(
            {
                "symbol": ["ABC", "XYZ"],
                "title": ["a", "x"],
                "source": ["wire", "wire"],
                "published_at": ["2026-10-01T09:00:00Z", "2026-10-01T10:00:00Z"],
                "sentiment_score": [0.5, -0.4],
            }
        )
    )
    bars = load_price_bars(
        pd.DataFrame(
            {
                "symbol": ["ABC"],
                "timestamp": ["2026-10-01T09:00:00Z"],
                "Close": [100],
            }
        )
    )
    assert validate_coverage(records, bars) == 1
