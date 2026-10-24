"""News sentiment intelligence for AI trading research."""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

POSITIVE = {
    "beat",
    "growth",
    "profit",
    "surge",
    "strong",
    "upgrade",
    "positive",
    "record",
    "bullish",
}
NEGATIVE = {
    "miss",
    "loss",
    "fall",
    "drop",
    "weak",
    "downgrade",
    "negative",
    "fraud",
    "bearish",
}


@dataclass(frozen=True)
class SentimentResult:
    """Deterministic headline sentiment result."""

    score: float
    label: str
    positive_terms: int
    negative_terms: int


def score_headline(headline: str) -> SentimentResult:
    """Score a headline using a small transparent finance lexicon."""
    words = re.findall(r"[a-z]+", str(headline).lower())
    positive = sum(word in POSITIVE for word in words)
    negative = sum(word in NEGATIVE for word in words)
    total = positive + negative
    score = 0.0 if total == 0 else (positive - negative) / total
    label = "POSITIVE" if score > 0.0 else "NEGATIVE" if score < 0.0 else "NEUTRAL"
    return SentimentResult(round(score, 3), label, positive, negative)


def summarize_news(news: pd.DataFrame) -> pd.DataFrame:
    """Return transparent sentiment metrics for a headline table."""
    columns = ["headline", "score", "label", "positive_terms", "negative_terms"]
    if news.empty or "headline" not in news.columns:
        return pd.DataFrame(columns=columns)
    rows = []
    for headline in news["headline"].fillna(""):
        result = score_headline(str(headline))
        rows.append(
            {
                "headline": str(headline),
                "score": result.score,
                "label": result.label,
                "positive_terms": result.positive_terms,
                "negative_terms": result.negative_terms,
            }
        )
    return pd.DataFrame(rows, columns=columns)


def aggregate_sentiment(news: pd.DataFrame) -> dict[str, float | str]:
    """Aggregate headline sentiment without making a trading recommendation."""
    scored = summarize_news(news)
    if scored.empty:
        return {"sentiment_score": 0.0, "label": "NEUTRAL", "headlines": 0.0}
    score = float(scored["score"].mean())
    label = "POSITIVE" if score > 0.0 else "NEGATIVE" if score < 0.0 else "NEUTRAL"
    return {
        "sentiment_score": round(score, 3),
        "label": label,
        "headlines": float(len(scored)),
    }
