"""Chronological holdout evaluation for financial-news sentiment research."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline

from ai_trading.financial_sentiment_model import build_classifier
from ai_trading.news_schema import NewsRecord

SENTIMENT_LABELS = ("NEGATIVE", "NEUTRAL", "POSITIVE")


@dataclass(frozen=True)
class TimeAwareSentimentEvaluation:
    """Metrics from a strictly chronological train/test evaluation."""

    accuracy: float
    macro_f1: float
    labels: tuple[str, ...]
    confusion_matrix: list[list[int]]
    classification_report: dict[str, object]
    train_size: int
    test_size: int
    train_end: datetime
    test_start: datetime


def _record_text(record: NewsRecord) -> str:
    parts = [record.title]
    if record.summary:
        parts.append(record.summary)
    return " ".join(parts).strip()


def evaluate_classifier_time_aware(
    records: Sequence[NewsRecord],
    *,
    test_size: float = 0.25,
) -> TimeAwareSentimentEvaluation:
    """Fit on earlier publications and evaluate only on later publications.

    Records sharing a publication timestamp are kept in the same partition.
    This prevents a timestamp group from straddling the train/test boundary.
    """
    if not 0.0 < test_size < 1.0:
        raise ValueError("test_size must be between 0 and 1")
    if len(records) < 4:
        raise ValueError("At least four labeled news records are required")

    validated: list[tuple[datetime, str, str]] = []
    for record in records:
        if not record.sentiment_label:
            raise ValueError("Every evaluation record must have a sentiment_label")
        label = record.sentiment_label.upper()
        if label not in SENTIMENT_LABELS:
            raise ValueError(f"Unsupported sentiment label: {label}")
        text = _record_text(record)
        if not text:
            raise ValueError("Evaluation records must contain title or summary text")
        validated.append((record.published_at, text, label))

    validated.sort(key=lambda item: item[0])
    labels = [item[2] for item in validated]
    if len(set(labels)) < 2:
        raise ValueError("Evaluation data must contain at least two sentiment classes")

    split_index = int(len(validated) * (1.0 - test_size))
    split_index = max(1, min(split_index, len(validated) - 1))
    # Keep identical publication timestamps together in the later partition.
    while (
        split_index < len(validated) and validated[split_index][0] == validated[split_index - 1][0]
    ):
        split_index += 1
    if split_index >= len(validated):
        raise ValueError("Not enough distinct publication times for a chronological split")

    train = validated[:split_index]
    test = validated[split_index:]
    train_labels = [item[2] for item in train]
    test_labels = [item[2] for item in test]
    if len(set(train_labels)) < 2:
        raise ValueError("Chronological training period must contain at least two classes")

    train_texts = [item[1] for item in train]
    test_texts = [item[1] for item in test]
    label_order = tuple(sorted(set(labels)))

    model: Pipeline = build_classifier()
    model.fit(train_texts, train_labels)
    predictions = model.predict(test_texts)

    return TimeAwareSentimentEvaluation(
        accuracy=float(accuracy_score(test_labels, predictions)),
        macro_f1=float(f1_score(test_labels, predictions, average="macro", zero_division=0)),
        labels=label_order,
        confusion_matrix=confusion_matrix(test_labels, predictions, labels=list(label_order)).tolist(),
        classification_report=classification_report(
            test_labels,
            predictions,
            labels=list(label_order),
            output_dict=True,
            zero_division=0,
        ),
        train_size=len(train),
        test_size=len(test),
        train_end=train[-1][0],
        test_start=test[0][0],
    )
