from datetime import UTC, datetime, timedelta

import pytest

from ai_trading.financial_sentiment_time_eval import evaluate_classifier_time_aware
from ai_trading.news_schema import NewsRecord


def _record(title: str, label: str, day: int) -> NewsRecord:
    return NewsRecord(
        title=title,
        source="Test",
        published_at=datetime(2026, 10, day, tzinfo=UTC),
        sentiment_label=label,
    )


@pytest.fixture
def chronological_records() -> list[NewsRecord]:
    examples = [
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
    return [
        _record(title, label, day)
        for day, (title, label) in enumerate(examples, start=1)
    ]


def test_time_aware_evaluation_uses_later_records_for_test(
    chronological_records: list[NewsRecord],
) -> None:
    result = evaluate_classifier_time_aware(chronological_records)

    assert result.train_size + result.test_size == len(chronological_records)
    assert result.train_end < result.test_start
    assert result.test_size == 3
    assert 0.0 <= result.accuracy <= 1.0
    assert 0.0 <= result.macro_f1 <= 1.0
    assert len(result.confusion_matrix) == 3
    assert all(len(row) == 3 for row in result.confusion_matrix)


def test_records_with_same_timestamp_are_not_split() -> None:
    records = [
        _record("positive earnings", "POSITIVE", 1),
        _record("negative earnings", "NEGATIVE", 2),
        _record("neutral filing", "NEUTRAL", 3),
        _record("positive sales", "POSITIVE", 4),
        _record("negative outlook", "NEGATIVE", 5),
        _record("neutral announcement", "NEUTRAL", 5),
    ]

    result = evaluate_classifier_time_aware(records, test_size=0.33)

    assert result.train_end < result.test_start
    assert result.test_start.day == 5
    assert result.test_size == 2


@pytest.mark.parametrize("test_size", [0.0, 1.0, -0.1, 1.1])
def test_time_aware_evaluation_rejects_invalid_test_size(
    chronological_records: list[NewsRecord],
    test_size: float,
) -> None:
    with pytest.raises(ValueError, match="test_size"):
        evaluate_classifier_time_aware(chronological_records, test_size=test_size)


def test_time_aware_evaluation_rejects_unlabeled_records() -> None:
    records = [
        _record("positive earnings", "POSITIVE", 1),
        _record("negative earnings", "NEGATIVE", 2),
        _record("neutral filing", "NEUTRAL", 3),
        NewsRecord(
            title="missing label",
            source="Test",
            published_at=datetime(2026, 10, 4, tzinfo=UTC),
        ),
    ]

    with pytest.raises(ValueError, match="sentiment_label"):
        evaluate_classifier_time_aware(records)
