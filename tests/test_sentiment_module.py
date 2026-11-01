import math

import numpy as np
import pandas as pd
import pytest

from sentiment import (
    daily_sentiment,
    decayed_sentiment,
    information_coefficient,
    quantile_forward_returns,
    score_articles,
    score_text,
    sentiment_features,
    sentiment_signal,
)


def test_basic_polarity() -> None:
    assert score_text("Company posts record profit and strong growth").label == "POSITIVE"
    assert score_text("Shares plunge after fraud probe").label == "NEGATIVE"
    assert score_text("Company announces board meeting date").label == "NEUTRAL"


def test_negation_flips_sign() -> None:
    assert score_text("results were strong").score > 0
    assert score_text("results were not strong").score < 0


def test_intensifier_and_diminisher() -> None:
    base = score_text("profit rose").score
    assert score_text("profit rose sharply").score > base
    assert score_text("profit rose slightly").score < base


def test_phrase_beats_words() -> None:
    result = score_text("Firm misses estimates")
    assert result.score < -0.4
    assert "misses estimates" in result.hits


def test_score_bounded_and_robust_to_bad_input() -> None:
    assert -1.0 <= score_text("surge " * 200).score <= 1.0
    assert score_text(None).label == "NEUTRAL"  # type: ignore[arg-type]
    assert score_text(float("nan")).score == 0.0  # type: ignore[arg-type]
    assert score_text("").label == "NEUTRAL"


def _articles() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "title": ["Strong profit growth", "Shares plunge on fraud probe", "Board meeting"],
            "summary": ["", "", ""],
            "published": ["2026-10-01T10:00:00Z", 1759400000, "not a date"],
        }
    )


def test_score_articles_parses_mixed_dates() -> None:
    scored = score_articles(_articles())
    assert list(scored["label"]) == ["POSITIVE", "NEGATIVE", "NEUTRAL"]
    assert scored["published"].notna().sum() == 2
    assert score_articles([]).empty


def test_daily_drops_undated_and_aggregates() -> None:
    daily = daily_sentiment(score_articles(_articles()))
    assert daily["n_articles"].sum() == 2


def test_decay_is_point_in_time() -> None:
    scored = pd.DataFrame(
        {
            "published": pd.to_datetime(["2026-10-01", "2026-10-10"], utc=True),
            "score": [-0.8, 0.8],
        }
    )
    early = decayed_sentiment(scored, asof=pd.Timestamp("2026-10-02"))
    late = decayed_sentiment(scored, asof=pd.Timestamp("2026-10-10"))
    assert early["n"] == 1 and early["score"] == pytest.approx(-0.8)  # future article ignored
    assert late["n"] == 2 and late["score"] > 0.5  # recent positive dominates


def test_features_use_only_past_data() -> None:
    idx = pd.date_range("2026-01-01", periods=40, freq="D", name="date")
    rng = np.random.default_rng(0)
    base = pd.DataFrame({"score": rng.uniform(-1, 1, 40), "n_articles": 2}, index=idx)
    full = sentiment_features(base)
    truncated = sentiment_features(base.iloc[:30])
    pd.testing.assert_series_equal(full["zscore"].iloc[:30], truncated["zscore"], check_names=False)
    assert sentiment_features(pd.DataFrame()).empty


def test_signal_shrinkage_and_min_articles() -> None:
    assert sentiment_signal(0.9, 1)["label"] == "INSUFFICIENT_DATA"
    thin = sentiment_signal(0.5, 3)  # 0.5 * 3/6 = 0.25
    assert thin["shrunk_score"] == pytest.approx(0.25)
    assert thin["label"] == "BULLISH"
    assert sentiment_signal(-0.9, 30)["label"] == "BEARISH"
    assert sentiment_signal(0.05, 30)["label"] == "NEUTRAL"


def _prices_and_sentiment(predictive: bool) -> tuple[pd.Series, pd.Series]:
    rng = np.random.default_rng(1)
    days = pd.bdate_range("2025-01-01", periods=400)
    sent = pd.Series(rng.normal(size=len(days)), index=days)
    noise = rng.normal(0, 0.01, len(days))
    # return on day t+1 depends on sentiment of day t (lag-1 relationship)
    rets = noise + (0.01 * sent.shift(1).fillna(0) if predictive else 0)
    close = pd.Series(100 * np.exp(np.cumsum(rets)), index=days)
    return sent, close


def test_ic_detects_signal_and_rejects_noise() -> None:
    sent, close = _prices_and_sentiment(True)
    good = information_coefficient(sent, close, horizon=1, lag=0)
    assert good["ic"] > 0.4 and good["t_stat"] > 5
    sent, close = _prices_and_sentiment(False)
    bad = information_coefficient(sent, close, horizon=1, lag=0)
    assert abs(bad["ic"]) < 0.2


def test_ic_lag_prevents_lookahead() -> None:
    sent, close = _prices_and_sentiment(True)
    # Signal is only in the day right after; skipping it with lag=1 must destroy the edge.
    assert abs(information_coefficient(sent, close, horizon=1, lag=1)["ic"]) < 0.2


def test_ic_insufficient_data_is_nan() -> None:
    sent, close = _prices_and_sentiment(True)
    out = information_coefficient(sent.iloc[:10], close, min_obs=20)
    assert math.isnan(out["ic"])
    with pytest.raises(ValueError):
        information_coefficient(sent, close, horizon=0)


def test_quantile_returns_monotone_for_predictive_signal() -> None:
    sent, close = _prices_and_sentiment(True)
    table = quantile_forward_returns(sent, close, horizon=1, lag=0, buckets=3)
    assert list(table["bucket"]) == [1, 2, 3]
    assert table["mean_fwd_return"].iloc[-1] > table["mean_fwd_return"].iloc[0]
