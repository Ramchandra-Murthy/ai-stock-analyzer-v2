"""Rule-based finance text sentiment with negation, intensifiers and phrases."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

import pandas as pd

from sentiment.lexicon import (
    DIMINISHERS,
    INTENSIFIERS,
    NEGATORS,
    PHRASES,
    WORD_WEIGHTS,
)

NEGATION_WINDOW = 3  # tokens before a hit that can flip it
MODIFIER_WINDOW = 2  # tokens before a hit that can scale it
NEGATION_FACTOR = -0.8  # flipped hits are slightly dampened ("not good" != "bad")
NORMALIZATION_ALPHA = 2.0  # score = s / sqrt(s^2 + alpha), bounded in (-1, 1)
NEUTRAL_BAND = 0.05

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")


@dataclass(frozen=True)
class TextSentiment:
    """Sentiment of one text. ``score`` is in [-1, 1]; ``hits`` are the matched terms."""

    score: float
    label: str
    positive_hits: int
    negative_hits: int
    hits: tuple[str, ...]


def _tokenize(text: str) -> list[str]:
    cleaned = str(text).lower().replace("-", " ").replace("’", "'")
    return [t.replace("'", "") for t in _TOKEN_RE.findall(cleaned)]


def _scale(tokens: list[str], idx: int) -> float:
    """Return the modifier multiplier applied to the hit at ``idx``."""
    factor = 1.0
    # "sharply higher" (before) and "rose sharply" (one token after) both count.
    for tok in tokens[max(0, idx - MODIFIER_WINDOW) : idx] + tokens[idx + 1 : idx + 2]:
        factor *= INTENSIFIERS.get(tok, DIMINISHERS.get(tok, 1.0))
    return factor


def _negated(tokens: list[str], idx: int) -> bool:
    return any(t in NEGATORS for t in tokens[max(0, idx - NEGATION_WINDOW) : idx])


def score_text(text: str) -> TextSentiment:
    """Score a headline or short article. Empty or non-string input scores neutral."""
    if text is None or (isinstance(text, float) and math.isnan(text)):
        return TextSentiment(0.0, "NEUTRAL", 0, 0, ())
    tokens = _tokenize(str(text))
    consumed = [False] * len(tokens)
    contributions: list[tuple[str, float]] = []

    # Phrases first so "beats estimates" is not scored as two separate words.
    for n in (3, 2):
        for i in range(len(tokens) - n + 1):
            if any(consumed[i : i + n]):
                continue
            phrase = " ".join(tokens[i : i + n])
            if phrase in PHRASES:
                weight = PHRASES[phrase]
                if weight and _negated(tokens, i):
                    weight *= NEGATION_FACTOR
                if weight:
                    contributions.append((phrase, weight * _scale(tokens, i)))
                for j in range(i, i + n):
                    consumed[j] = True

    for i, tok in enumerate(tokens):
        if consumed[i] or tok not in WORD_WEIGHTS:
            continue
        weight = WORD_WEIGHTS[tok]
        if _negated(tokens, i):
            weight *= NEGATION_FACTOR
        contributions.append((tok, weight * _scale(tokens, i)))

    total = sum(w for _, w in contributions)
    score = total / math.sqrt(total * total + NORMALIZATION_ALPHA) if total else 0.0
    score = max(-1.0, min(1.0, score))
    label = (
        "POSITIVE" if score > NEUTRAL_BAND else "NEGATIVE" if score < -NEUTRAL_BAND else "NEUTRAL"
    )
    return TextSentiment(
        round(score, 4),
        label,
        sum(w > 0 for _, w in contributions),
        sum(w < 0 for _, w in contributions),
        tuple(t for t, _ in contributions),
    )


def score_articles(
    articles: list[dict[str, Any]] | pd.DataFrame,
    *,
    title_key: str = "title",
    summary_key: str = "summary",
    date_key: str = "published",
    title_weight: float = 0.7,
) -> pd.DataFrame:
    """Score article records (e.g. from ``services.news_service.get_company_news``).

    Title and summary are scored separately and blended (headlines carry most signal).
    ``published`` accepts ISO strings or unix seconds; unparseable dates become NaT.
    """
    columns = ["published", "title", "score", "label", "title_score", "summary_score", "hits"]
    frame = pd.DataFrame(articles) if not isinstance(articles, pd.DataFrame) else articles
    if frame.empty or title_key not in frame.columns:
        return pd.DataFrame(columns=columns)
    rows = []
    for _, rec in frame.iterrows():
        title = score_text(rec.get(title_key, ""))
        summary_raw = rec.get(summary_key, "") if summary_key in frame.columns else ""
        summary = score_text(summary_raw)
        has_summary = bool(str(summary_raw or "").strip()) and summary.hits
        blended = (
            title_weight * title.score + (1 - title_weight) * summary.score
            if has_summary
            else title.score
        )
        label = (
            "POSITIVE"
            if blended > NEUTRAL_BAND
            else "NEGATIVE"
            if blended < -NEUTRAL_BAND
            else "NEUTRAL"
        )
        rows.append(
            {
                "published": rec.get(date_key) if date_key in frame.columns else None,
                "title": str(rec.get(title_key, "")),
                "score": round(blended, 4),
                "label": label,
                "title_score": title.score,
                "summary_score": summary.score,
                "hits": ", ".join(title.hits + summary.hits),
            }
        )
    out = pd.DataFrame(rows, columns=columns)
    out["published"] = _parse_dates(out["published"])
    return out


def _parse_dates(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    as_unix = pd.to_datetime(numeric, unit="s", utc=True, errors="coerce")
    as_text = pd.to_datetime(
        values.where(numeric.isna()), utc=True, errors="coerce", format="mixed"
    )
    return as_unix.fillna(as_text)
