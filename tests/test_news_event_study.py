"""Tests for financial-news event-window return analysis."""

from datetime import UTC, datetime

import pytest

from ai_trading.news_event_study import PriceBar, analyze_news_event_returns
from ai_trading.news_schema import NewsRecord


def _record(
    published_at: str = "2026-01-02T10:00:00Z",
    label: str = "POSITIVE",
    symbol: str = "ABC",
) -> NewsRecord:
    return NewsRecord(
        title="Company reports results",
        source="Test",
        published_at=published_at,
        symbol=symbol,
        sentiment_label=label,
    )


def _bars() -> list[PriceBar]:
    return [
        PriceBar(datetime(2026, 1, day, 15, tzinfo=UTC), close)
        for day, close in [(1, 100), (2, 101), (3, 103), (4, 102), (5, 105), (6, 106)]
    ]


def test_forward_returns_use_first_bar_at_or_after_publication() -> None:
    report = analyze_news_event_returns([_record()], {"ABC": _bars()}, horizons=(1, 3))

    event = report.events[0]
    assert event.anchor_at == datetime(2026, 1, 2, 15, tzinfo=UTC)
    assert event.anchor_close == 101
    assert event.forward_returns[1] == pytest.approx(103 / 101 - 1)
    assert event.forward_returns[3] == pytest.approx(106 / 101 - 1)


def test_summary_groups_by_label_and_horizon() -> None:
    records = [
        _record("2026-01-02T10:00:00Z", "POSITIVE"),
        _record("2026-01-03T10:00:00Z", "NEGATIVE"),
    ]
    report = analyze_news_event_returns(records, {"ABC": _bars()}, horizons=(1,))

    assert {(item.sentiment_label, item.event_count) for item in report.summary} == {
        ("POSITIVE", 1),
        ("NEGATIVE", 1),
    }


def test_missing_symbol_or_price_history_is_skipped() -> None:
    report = analyze_news_event_returns([_record(symbol="MISSING")], {"ABC": _bars()})

    assert report.events == ()
    assert report.skipped_events == 1


def test_events_without_enough_forward_bars_are_skipped() -> None:
    short_bars = _bars()[:2]
    report = analyze_news_event_returns(
        [_record("2026-01-02T10:00:00Z")],
        {"ABC": short_bars},
        horizons=(2,),
    )

    assert report.events == ()
    assert report.skipped_events == 1


def test_naive_price_timestamp_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        PriceBar(datetime(2026, 1, 1), 100)


def test_duplicate_price_timestamps_are_rejected() -> None:
    bars = _bars()
    bars.append(bars[-1])
    with pytest.raises(ValueError, match="duplicate"):
        analyze_news_event_returns([_record()], {"ABC": bars})


def test_invalid_horizons_are_rejected() -> None:
    with pytest.raises(ValueError, match="positive integers"):
        analyze_news_event_returns([_record()], {"ABC": _bars()}, horizons=(0,))
