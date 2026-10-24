import pandas as pd
import pytest

from ai_trading.news_sentiment import aggregate_sentiment, score_headline, summarize_news


def test_positive_headline() -> None:
    result = score_headline("Company reports strong profit growth and record sales")
    assert result.label == "POSITIVE"
    assert result.score == pytest.approx(1.0)


def test_negative_headline() -> None:
    result = score_headline("Company reports weak profit and loss after downgrade")
    assert result.label == "NEGATIVE"
    assert result.score < 0.0


def test_neutral_and_aggregate() -> None:
    news = pd.DataFrame({"headline": ["Company update", "Strong growth", "Weak outlook"]})
    summary = summarize_news(news)
    aggregate = aggregate_sentiment(news)
    assert len(summary) == 3
    assert aggregate["headlines"] == 3.0
    assert aggregate["label"] == "NEUTRAL"


def test_empty_news() -> None:
    assert aggregate_sentiment(pd.DataFrame())["label"] == "NEUTRAL"
