from datetime import datetime, timezone

import pytest

from ai_trading.news_schema import NewsRecord


def test_normalizes_symbol_and_timestamps_to_utc() -> None:
    record = NewsRecord(
        title="  Reliance reports growth ",
        source="Example",
        symbol=" reliance ",
        published_at="2026-10-31T10:00:00+05:30",
        ingested_at="2026-10-31T05:00:00Z",
    )

    assert record.symbol == "RELIANCE"
    assert record.title == "Reliance reports growth"
    assert record.published_at == datetime(2026, 10, 31, 4, 30, tzinfo=timezone.utc)
    assert record.ingested_at == datetime(2026, 10, 31, 5, 0, tzinfo=timezone.utc)


def test_from_mapping_supports_news_service_shape() -> None:
    record = NewsRecord.from_mapping(
        {
            "title": "Company update",
            "publisher": "Example News",
            "published": "2026-10-31T10:00:00Z",
            "link": "https://example.com/article",
            "summary": "A short summary",
            "symbol": "TCS",
        }
    )

    assert record.source == "Example News"
    assert record.symbol == "TCS"
    assert record.url == "https://example.com/article"
    assert record.summary == "A short summary"


def test_from_mapping_supports_yahoo_nested_content() -> None:
    record = NewsRecord.from_mapping(
        {
            "content": {
                "title": "Nested headline",
                "provider": {"displayName": "Publisher"},
                "pubDate": "2026-10-31T10:00:00Z",
                "canonicalUrl": {"url": "https://example.com/story"},
            }
        }
    )

    assert record.title == "Nested headline"
    assert record.source == "Publisher"
    assert record.published_at.tzinfo == timezone.utc


def test_unix_timestamp_is_supported() -> None:
    record = NewsRecord(
        title="Headline",
        source="Publisher",
        published_at=1793440800,
    )
    assert record.published_at.tzinfo == timezone.utc


@pytest.mark.parametrize("timestamp", ["", "2026-10-31T10:00:00", "not-a-date"])
def test_rejects_missing_or_naive_timestamp(timestamp: str) -> None:
    with pytest.raises(ValueError):
        NewsRecord(title="Headline", source="Publisher", published_at=timestamp)


@pytest.mark.parametrize(
    ("field", "value"),
    [("sentiment_score", 1.1), ("sentiment_confidence", -0.1)],
)
def test_rejects_out_of_range_sentiment(field: str, value: float) -> None:
    with pytest.raises(ValueError):
        NewsRecord(
            title="Headline",
            source="Publisher",
            published_at="2026-10-31T10:00:00Z",
            **{field: value},
        )


def test_deduplication_key_is_stable_and_symbol_scoped() -> None:
    base = {
        "title": "Headline",
        "source": "Publisher",
        "published_at": "2026-10-31T10:00:00Z",
        "url": "https://example.com/story",
    }
    first = NewsRecord(**base, symbol="TCS")
    same = NewsRecord(**base, symbol="TCS")
    other_symbol = NewsRecord(**base, symbol="INFY")

    assert first.deduplication_key == same.deduplication_key
    assert first.deduplication_key != other_symbol.deduplication_key


def test_to_dict_is_json_friendly() -> None:
    record = NewsRecord(
        title="Headline",
        source="Publisher",
        published_at="2026-10-31T10:00:00Z",
    )
    result = record.to_dict()
    assert result["published_at"] == "2026-10-31T10:00:00+00:00"
    assert result["ingested_at"].endswith("+00:00")
