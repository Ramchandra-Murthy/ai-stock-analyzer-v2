"""Historical AI signal ledger and outcome analytics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pandas as pd


@dataclass(frozen=True)
class SignalRecord:
    """A timestamped AI signal with its model inputs and later outcome."""

    symbol: str
    exchange: str
    timestamp: datetime
    signal: str
    probability_up_pct: float
    confidence_pct: float
    validation_pct: float
    trend_pct: float
    entry_price: float
    horizon_days: int
    outcome_price: float | None = None
    raw_confidence_pct: float | None = None
    adaptive_confidence_pct: float | None = None
    adaptive_adjustment_pct: float | None = None
    adaptive_samples: int = 0

    @property
    def return_pct(self) -> float | None:
        """Return price change, signed by the recorded signal direction."""
        if self.outcome_price is None or self.entry_price <= 0:
            return None
        raw_return = (self.outcome_price / self.entry_price - 1.0) * 100.0
        if self.signal == "SHORT":
            return -raw_return
        if self.signal == "NEUTRAL":
            return 0.0
        return raw_return


def record_signal(
    *,
    symbol: str,
    exchange: str,
    signal: str,
    probability_up: float,
    confidence_pct: float,
    validation_pct: float,
    trend_pct: float,
    entry_price: float,
    horizon_days: int,
    timestamp: datetime | None = None,
    raw_confidence_pct: float | None = None,
    adaptive_confidence_pct: float | None = None,
    adaptive_adjustment_pct: float | None = None,
    adaptive_samples: int = 0,
) -> SignalRecord:
    """Create a validated signal record."""
    if signal not in {"LONG", "SHORT", "NEUTRAL"}:
        raise ValueError("signal must be LONG, SHORT or NEUTRAL")
    if not 0.0 <= probability_up <= 1.0:
        raise ValueError("probability_up must be between 0 and 1")
    if confidence_pct < 0.0 or validation_pct < 0.0 or trend_pct < 0.0:
        raise ValueError("signal percentages must be non-negative")
    if entry_price <= 0.0:
        raise ValueError("entry_price must be positive")
    if adaptive_samples < 0:
        raise ValueError("adaptive_samples must be non-negative")
    if horizon_days < 1:
        raise ValueError("horizon_days must be at least 1")
    return SignalRecord(
        symbol=symbol,
        exchange=exchange,
        timestamp=timestamp or datetime.now(UTC),
        signal=signal,
        probability_up_pct=round(probability_up * 100.0, 1),
        confidence_pct=round(confidence_pct, 1),
        validation_pct=round(validation_pct, 1),
        trend_pct=round(trend_pct, 1),
        entry_price=float(entry_price),
        horizon_days=horizon_days,
        raw_confidence_pct=(
            round(raw_confidence_pct, 1) if raw_confidence_pct is not None else None
        ),
        adaptive_confidence_pct=(
            round(adaptive_confidence_pct, 1) if adaptive_confidence_pct is not None else None
        ),
        adaptive_adjustment_pct=(
            round(adaptive_adjustment_pct, 1) if adaptive_adjustment_pct is not None else None
        ),
        adaptive_samples=adaptive_samples,
    )


def attach_outcomes(
    records: list[SignalRecord],
    prices: dict[str, float],
) -> pd.DataFrame:
    """Attach supplied outcome prices and calculate signed returns."""
    rows = []
    for record in records:
        outcome = prices.get(record.symbol)
        completed = outcome is not None
        updated = SignalRecord(**{**record.__dict__, "outcome_price": outcome})
        rows.append(
            {
                "timestamp": updated.timestamp,
                "symbol": updated.symbol,
                "exchange": updated.exchange,
                "signal": updated.signal,
                "probability_up_pct": updated.probability_up_pct,
                "confidence_pct": updated.confidence_pct,
                "raw_confidence_pct": updated.raw_confidence_pct,
                "adaptive_confidence_pct": updated.adaptive_confidence_pct,
                "adaptive_adjustment_pct": updated.adaptive_adjustment_pct,
                "adaptive_samples": updated.adaptive_samples,
                "validation_pct": updated.validation_pct,
                "trend_pct": updated.trend_pct,
                "entry_price": updated.entry_price,
                "outcome_price": updated.outcome_price,
                "return_pct": updated.return_pct,
                "horizon_days": updated.horizon_days,
                "completed": completed,
            }
        )
    return pd.DataFrame(rows)


def summarize_outcomes(history: pd.DataFrame) -> pd.DataFrame:
    """Summarize completed signal outcomes by signal type."""
    if history.empty:
        return pd.DataFrame(
            columns=["signal", "signals", "completed", "win_rate_pct", "avg_return_pct"]
        )
    completed = history[history["completed"]].copy()
    if completed.empty:
        return pd.DataFrame(
            columns=["signal", "signals", "completed", "win_rate_pct", "avg_return_pct"]
        )
    summary = (
        completed.assign(
            win=completed["return_pct"] > 0.0,
        )
        .groupby("signal", as_index=False)
        .agg(
            signals=("signal", "size"),
            completed=("completed", "sum"),
            win_rate_pct=("win", lambda values: values.mean() * 100.0),
            avg_return_pct=("return_pct", "mean"),
        )
    )
    return summary.sort_values("signal").reset_index(drop=True)
