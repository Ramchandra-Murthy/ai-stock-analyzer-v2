"""Point-in-time event-window returns for financial-news sentiment research."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import mean, median

from ai_trading.news_schema import NewsRecord


def _timestamp(value: datetime | str | int | float) -> datetime:
    """Normalize timestamps to timezone-aware UTC."""
    if isinstance(value, (int, float)):
        parsed = datetime.fromtimestamp(value, tz=UTC)
    elif isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        parsed = datetime.fromisoformat(text)
    elif isinstance(value, datetime):
        parsed = value
    else:
        raise TypeError("timestamp must be datetime, ISO-8601 string, or Unix timestamp")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return parsed.astimezone(UTC)


@dataclass(frozen=True)
class PriceBar:
    """A price observation; timestamp should represent when close is observable."""

    timestamp: datetime | str | int | float
    close: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "timestamp", _timestamp(self.timestamp))
        close = float(self.close)
        if close <= 0:
            raise ValueError("close must be positive")
        object.__setattr__(self, "close", close)


@dataclass(frozen=True)
class EventReturn:
    """Forward returns for one news record anchored to an observable price bar."""

    symbol: str
    published_at: datetime
    sentiment_label: str
    anchor_at: datetime
    anchor_close: float
    forward_returns: Mapping[int, float]


@dataclass(frozen=True)
class EventStudySummary:
    """Aggregate forward returns by sentiment label and horizon."""

    sentiment_label: str
    horizon: int
    event_count: int
    mean_return: float
    median_return: float


@dataclass(frozen=True)
class EventStudyReport:
    """Individual event returns and grouped descriptive summaries."""

    events: tuple[EventReturn, ...]
    summary: tuple[EventStudySummary, ...]
    skipped_events: int


def analyze_news_event_returns(
    records: Sequence[NewsRecord],
    prices_by_symbol: Mapping[str, Sequence[PriceBar]],
    *,
    horizons: Sequence[int] = (1, 3, 5),
) -> EventStudyReport:
    """Measure close-to-close forward returns after news publication.

    The anchor is the first supplied price bar timestamped at or after publication.
    Horizon 1 is the next bar's close relative to the anchor close. Price bars
    must be supplied by the caller; this function performs no data retrieval.
    Returns are descriptive event-study measurements, not trading signals.
    """
    normalized_horizons = tuple(sorted(set(horizons)))
    if not normalized_horizons or any(
        not isinstance(horizon, int) or isinstance(horizon, bool) or horizon < 1
        for horizon in normalized_horizons
    ):
        raise ValueError("horizons must contain positive integers")

    bars_by_symbol: dict[str, tuple[PriceBar, ...]] = {}
    for symbol, bars in prices_by_symbol.items():
        key = str(symbol).strip().upper()
        ordered = tuple(sorted(bars, key=lambda bar: bar.timestamp))
        if not key:
            raise ValueError("price symbols must not be empty")
        if any(
            ordered[index].timestamp == ordered[index - 1].timestamp
            for index in range(1, len(ordered))
        ):
            raise ValueError(f"duplicate price timestamps for {key}")
        bars_by_symbol[key] = ordered

    events: list[EventReturn] = []
    skipped = 0
    grouped: dict[tuple[str, int], list[float]] = defaultdict(list)

    for record in records:
        if not record.symbol or not record.sentiment_label:
            skipped += 1
            continue
        bars = bars_by_symbol.get(record.symbol.upper(), ())
        anchor_index = next(
            (index for index, bar in enumerate(bars) if bar.timestamp >= record.published_at),
            None,
        )
        if anchor_index is None:
            skipped += 1
            continue

        anchor = bars[anchor_index]
        forward_returns: dict[int, float] = {}
        for horizon in normalized_horizons:
            target_index = anchor_index + horizon
            if target_index < len(bars):
                value = bars[target_index].close / anchor.close - 1.0
                forward_returns[horizon] = value
                grouped[(record.sentiment_label, horizon)].append(value)

        if not forward_returns:
            skipped += 1
            continue
        events.append(
            EventReturn(
                symbol=record.symbol.upper(),
                published_at=record.published_at,
                sentiment_label=record.sentiment_label,
                anchor_at=anchor.timestamp,
                anchor_close=anchor.close,
                forward_returns=forward_returns,
            )
        )

    summaries = tuple(
        EventStudySummary(
            sentiment_label=label,
            horizon=horizon,
            event_count=len(values),
            mean_return=mean(values),
            median_return=median(values),
        )
        for (label, horizon), values in sorted(grouped.items())
    )
    return EventStudyReport(tuple(events), summaries, skipped)
