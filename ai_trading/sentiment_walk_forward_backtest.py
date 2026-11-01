"""Chronological walk-forward evaluation for point-in-time news sentiment signals."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import pandas as pd

from ai_trading.news_schema import NewsRecord


@dataclass(frozen=True)
class SentimentWalkForwardResult:
    """Event-level outcomes and chronological fold summaries."""

    events: pd.DataFrame
    folds: pd.DataFrame


def _validate_bars(frame: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise ValueError("Price bars must use a DatetimeIndex")
    if frame.index.tz is None:
        raise ValueError("Price-bar timestamps must be timezone-aware")
    if "Close" not in frame.columns:
        raise ValueError("Price bars must contain a Close column")
    bars = frame.copy()
    bars.index = bars.index.tz_convert("UTC")
    bars = bars.sort_index()
    if bars.index.has_duplicates:
        raise ValueError("Price-bar timestamps must be unique")
    bars["Close"] = pd.to_numeric(bars["Close"], errors="coerce")
    return bars


def _fold_metrics(events: pd.DataFrame, fold: int) -> dict[str, float | int | None]:
    returns = events["net_return"].astype(float)
    equity = (1.0 + returns).cumprod()
    drawdown = equity / equity.cummax() - 1.0
    wins = returns[returns > 0.0]
    losses = returns[returns < 0.0]
    gross_profit = float(wins.sum())
    gross_loss = float(-losses.sum())
    return {
        "fold": fold,
        "events": int(len(events)),
        "total_return": float(equity.iloc[-1] - 1.0) if len(equity) else 0.0,
        "mean_return": float(returns.mean()) if len(returns) else 0.0,
        "win_rate": float((returns > 0.0).mean()) if len(returns) else 0.0,
        "max_drawdown": float(drawdown.min()) if len(drawdown) else 0.0,
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else None,
    }


def evaluate_sentiment_walk_forward(
    records: Sequence[NewsRecord],
    bars_by_symbol: Mapping[str, pd.DataFrame],
    *,
    horizon: int = 5,
    folds: int = 4,
    sentiment_threshold: float = 0.1,
    transaction_cost_bps: float = 10.0,
) -> SentimentWalkForwardResult:
    """Evaluate news signals over chronological, non-overlapping event folds.

    Publication timestamps determine signal availability. A signal is evaluated
    using the first bar at or after publication as its decision bar, enters at
    the next bar's close, and exits after the configured number of bars.
    The fixed threshold is not fitted on any fold. This is research-only.
    """
    if horizon < 1:
        raise ValueError("horizon must be at least 1")
    if folds < 2:
        raise ValueError("folds must be at least 2")
    if not 0.0 <= sentiment_threshold <= 1.0:
        raise ValueError("sentiment_threshold must be between 0 and 1")
    if transaction_cost_bps < 0:
        raise ValueError("transaction_cost_bps must be non-negative")

    normalized_bars = {
        symbol.upper(): _validate_bars(frame) for symbol, frame in bars_by_symbol.items()
    }
    rows: list[dict[str, object]] = []
    for record in sorted(records, key=lambda item: item.published_at):
        if record.symbol is None or record.symbol.upper() not in normalized_bars:
            continue
        if record.sentiment_score is None:
            continue
        score = float(record.sentiment_score)
        if abs(score) < sentiment_threshold:
            continue
        bars = normalized_bars[record.symbol.upper()]
        published_at = pd.Timestamp(record.published_at).tz_convert("UTC")
        decision_index = int(bars.index.searchsorted(published_at, side="left"))
        entry_index = decision_index + 1
        exit_index = entry_index + horizon - 1
        if decision_index >= len(bars) or exit_index >= len(bars):
            continue
        entry = float(bars["Close"].iloc[entry_index])
        exit_price = float(bars["Close"].iloc[exit_index])
        if not (pd.notna(entry) and pd.notna(exit_price) and entry > 0.0 and exit_price > 0.0):
            continue
        direction = 1.0 if score > 0.0 else -1.0
        gross_return = direction * (exit_price / entry - 1.0)
        net_return = gross_return - 2.0 * transaction_cost_bps / 10000.0
        rows.append(
            {
                "symbol": record.symbol.upper(),
                "published_at": published_at,
                "decision_at": bars.index[decision_index],
                "entry_at": bars.index[entry_index],
                "exit_at": bars.index[exit_index],
                "sentiment_score": score,
                "signal": "LONG" if direction > 0 else "SHORT",
                "gross_return": gross_return,
                "net_return": net_return,
            }
        )

    event_columns = [
        "symbol", "published_at", "decision_at", "entry_at", "exit_at",
        "sentiment_score", "signal", "gross_return", "net_return",
    ]
    events = pd.DataFrame(rows, columns=event_columns)
    if events.empty:
        return SentimentWalkForwardResult(events, pd.DataFrame())

    events = events.sort_values("published_at", kind="stable").reset_index(drop=True)
    fold_count = min(folds, len(events))
    events["fold"] = (
        pd.Series(range(len(events))).mul(fold_count).floordiv(len(events)).add(1).to_numpy()
    )
    fold_rows = [
        _fold_metrics(group.reset_index(drop=True), int(fold))
        for fold, group in events.groupby("fold", sort=True)
    ]
    return SentimentWalkForwardResult(events, pd.DataFrame(fold_rows))
