"""Validated, point-in-time schema for financial news and sentiment records."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _parse_timestamp(value: datetime | str | int | float) -> datetime:
    """Parse a timestamp and require timezone information."""
    if isinstance(value, (int, float)):
        parsed = datetime.fromtimestamp(value, tz=timezone.utc)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("published_at must not be empty")
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError("timestamp must be ISO-8601 or a Unix timestamp") from exc
    elif isinstance(value, datetime):
        parsed = value
    else:
        raise TypeError("timestamp must be datetime, ISO-8601 string, or Unix timestamp")

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


@dataclass(frozen=True)
class NewsRecord:
    """One company-linked news item with point-in-time metadata.

    A record represents one article-to-symbol mapping. Keep publication time
    separate from ingestion time to prevent look-ahead leakage in research.
    """

    title: str
    source: str
    published_at: datetime | str | int | float
    symbol: str | None = None
    ingested_at: datetime | str | int | float = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    url: str | None = None
    summary: str | None = None
    event_type: str | None = None
    sentiment_score: float | None = None
    sentiment_label: str | None = None
    sentiment_confidence: float | None = None
    model_version: str | None = None

    def __post_init__(self) -> None:
        title = str(self.title).strip()
        source = str(self.source).strip()
        if not title:
            raise ValueError("title must not be empty")
        if not source:
            raise ValueError("source must not be empty")

        object.__setattr__(self, "title", title)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "published_at", _parse_timestamp(self.published_at))
        object.__setattr__(self, "ingested_at", _parse_timestamp(self.ingested_at))

        symbol = _optional_text(self.symbol)
        object.__setattr__(self, "symbol", symbol.upper() if symbol else None)
        for name in ("url", "summary", "event_type", "sentiment_label", "model_version"):
            object.__setattr__(self, name, _optional_text(getattr(self, name)))

        if self.sentiment_score is not None:
            score = float(self.sentiment_score)
            if not -1.0 <= score <= 1.0:
                raise ValueError("sentiment_score must be between -1 and 1")
            object.__setattr__(self, "sentiment_score", score)

        if self.sentiment_confidence is not None:
            confidence = float(self.sentiment_confidence)
            if not 0.0 <= confidence <= 1.0:
                raise ValueError("sentiment_confidence must be between 0 and 1")
            object.__setattr__(self, "sentiment_confidence", confidence)

        if self.sentiment_label is not None:
            label = self.sentiment_label.upper()
            if label not in {"POSITIVE", "NEGATIVE", "NEUTRAL"}:
                raise ValueError("sentiment_label must be POSITIVE, NEGATIVE, or NEUTRAL")
            object.__setattr__(self, "sentiment_label", label)

    @classmethod
    def from_mapping(cls, item: dict[str, Any]) -> NewsRecord:
        """Build a record from normalized news-service or provider-style fields."""
        content = item.get("content")
        if isinstance(content, dict):
            item = {**content, **item}

        provider = item.get("provider") or item.get("publisher") or item.get("source")
        if isinstance(provider, dict):
            provider = provider.get("displayName") or provider.get("name")

        published = (
            item.get("published_at")
            or item.get("published")
            or item.get("pubDate")
            or item.get("providerPublishTime")
        )
        return cls(
            title=item.get("title") or item.get("headline") or "",
            source=provider or "Unknown",
            published_at=published,
            ingested_at=item.get("ingested_at") or datetime.now(timezone.utc),
            symbol=item.get("symbol"),
            url=item.get("url") or item.get("link"),
            summary=item.get("summary") or item.get("description"),
            event_type=item.get("event_type"),
            sentiment_score=item.get("sentiment_score"),
            sentiment_label=item.get("sentiment_label"),
            sentiment_confidence=item.get("sentiment_confidence"),
            model_version=item.get("model_version"),
        )

    @property
    def deduplication_key(self) -> str:
        """Return a stable hash for duplicate detection within a symbol."""
        symbol = self.symbol or ""
        if self.url:
            identity = f"{symbol}|url|{self.url.strip()}"
        else:
            normalized_title = re.sub(r"\s+", " ", self.title).casefold()
            published_minute = self.published_at.replace(second=0, microsecond=0).isoformat()
            identity = f"{symbol}|{self.source.casefold()}|{normalized_title}|{published_minute}"
        return hashlib.sha256(identity.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly representation with UTC ISO timestamps."""
        return {
            "symbol": self.symbol,
            "title": self.title,
            "source": self.source,
            "published_at": self.published_at.isoformat(),
            "ingested_at": self.ingested_at.isoformat(),
            "url": self.url,
            "summary": self.summary,
            "event_type": self.event_type,
            "sentiment_score": self.sentiment_score,
            "sentiment_label": self.sentiment_label,
            "sentiment_confidence": self.sentiment_confidence,
            "model_version": self.model_version,
        }
