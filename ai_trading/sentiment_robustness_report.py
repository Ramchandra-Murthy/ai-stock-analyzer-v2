"""CSV input normalization for the sentiment robustness research report."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from ai_trading.news_schema import NewsRecord


def load_news_records(frame: pd.DataFrame) -> list[NewsRecord]:
    """Normalize uploaded news rows into point-in-time sentiment records."""
    required = {"symbol", "title", "source", "published_at", "sentiment_score"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"news CSV is missing required columns: {', '.join(sorted(missing))}")

    records: list[NewsRecord] = []
    for row in frame.to_dict(orient="records"):
        published_at = pd.to_datetime(row["published_at"], utc=True, errors="coerce")
        score = pd.to_numeric(row["sentiment_score"], errors="coerce")
        if pd.isna(published_at) or pd.isna(score):
            continue
        records.append(
            NewsRecord(
                symbol=str(row["symbol"]).strip(),
                title=str(row["title"]).strip(),
                source=str(row["source"]).strip() or "Uploaded CSV",
                published_at=published_at.to_pydatetime(),
                sentiment_score=float(score),
                url=str(row.get("url", "")).strip() or None,
            )
        )
    if not records:
        raise ValueError("news CSV contains no rows with valid timestamps and sentiment scores")
    return records


def load_price_bars(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Normalize uploaded symbol/timestamp/Close bars for backtesting."""
    required = {"symbol", "timestamp", "Close"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"price CSV is missing required columns: {', '.join(sorted(missing))}")

    data = frame.copy()
    data["symbol"] = data["symbol"].astype(str).str.strip().str.upper()
    data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True, errors="coerce")
    data["Close"] = pd.to_numeric(data["Close"], errors="coerce")
    data = data.dropna(subset=["symbol", "timestamp", "Close"])
    data = data[(data["symbol"] != "") & (data["Close"] > 0.0)]
    if data.empty:
        raise ValueError("price CSV contains no valid positive Close prices")
    if data.duplicated(["symbol", "timestamp"]).any():
        raise ValueError("price CSV must have unique timestamps per symbol")

    return {
        symbol: group.set_index("timestamp")[["Close"]].sort_index()
        for symbol, group in data.groupby("symbol", sort=True)
    }


def validate_coverage(
    records: Sequence[NewsRecord], bars_by_symbol: dict[str, pd.DataFrame]
) -> int:
    """Count news rows whose symbols have uploaded price bars."""
    available = set(bars_by_symbol)
    return sum(record.symbol in available for record in records if record.symbol is not None)
