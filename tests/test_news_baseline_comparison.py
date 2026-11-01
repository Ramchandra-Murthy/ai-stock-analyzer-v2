from datetime import UTC, datetime

import pytest

from ai_trading.news_baseline_comparison import compare_sentiment_baselines
from ai_trading.news_schema import NewsRecord


def _record(title: str, label: str, day: int) -> NewsRecord:
    return NewsRecord(
        title=title,
        source="Test",
        published_at=datetime(2026, 10, day, tzinfo=UTC),
        sentiment_label=label,
    )


@pytest.fixture
def records() -> list[NewsRecord]:
    data = [
        ("profit growth beats estimates", "POSITIVE"),
        ("quarterly loss widens", "NEGATIVE"),
        ("routine board meeting announced", "NEUTRAL"),
        ("strong revenue growth", "POSITIVE"),
        ("weak outlook after earnings", "NEGATIVE"),
        ("company schedules investor call", "NEUTRAL"),
        ("record earnings and profit", "POSITIVE"),
        ("shares fall on disappointing results", "NEGATIVE"),
        ("routine exchange filing", "NEUTRAL"),
        ("sales surge above expectations", "POSITIVE"),
        ("revenue declines sharply", "NEGATIVE"),
        ("company announces meeting date", "NEUTRAL"),
    ]
    return [_record(title, label, day) for day, (title, label) in enumerate(data, 1)]


def test_comparison_uses_same_future_holdout_for_both_baselines(
    records: list[NewsRecord],
) -> None:
    result = compare_sentiment_baselines(records)

    assert result.train_size + result.test_size == len(records)
    assert result.train_end < result.test_start
    assert result.test_size == 3
    for metric in (
        result.model_accuracy,
        result.model_macro_f1,
        result.lexicon_accuracy,
        result.lexicon_macro_f1,
    ):
        assert 0.0 <= metric <= 1.0


def test_comparison_rejects_invalid_test_size(records: list[NewsRecord]) -> None:
    with pytest.raises(ValueError, match="test_size"):
        compare_sentiment_baselines(records, test_size=1.0)


def test_comparison_requires_labeled_records() -> None:
    records = [
        _record("positive growth", "POSITIVE", 1),
        _record("negative loss", "NEGATIVE", 2),
        _record("neutral filing", "NEUTRAL", 3),
        NewsRecord(
            title="missing label",
            source="Test",
            published_at=datetime(2026, 10, 4, tzinfo=UTC),
        ),
    ]
    with pytest.raises(ValueError, match="sentiment_label"):
        compare_sentiment_baselines(records)
