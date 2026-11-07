"""Historical AI signal ledger and outcome analytics."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime, time

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
    adjusted_entry_price: float | None = None
    outcome_price: float | None = None
    raw_confidence_pct: float | None = None
    adaptive_confidence_pct: float | None = None
    adaptive_adjustment_pct: float | None = None
    adaptive_samples: int = 0

    @property
    def market_return_pct(self) -> float | None:
        """Return the underlying asset price change, independent of signal direction."""
        entry_price = (
            self.adjusted_entry_price if self.adjusted_entry_price is not None else self.entry_price
        )
        if self.outcome_price is None or entry_price <= 0:
            return None
        return (self.outcome_price / entry_price - 1.0) * 100.0

    @property
    def return_pct(self) -> float | None:
        """Return the directional strategy result; neutral signals are not trades."""
        market_return = self.market_return_pct
        if market_return is None or self.signal == "NEUTRAL":
            return None
        return -market_return if self.signal == "SHORT" else market_return


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
    adjusted_entry_price: float | None = None,
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
    if not math.isfinite(float(entry_price)) or entry_price <= 0.0:
        raise ValueError("entry_price must be finite and positive")
    if adjusted_entry_price is not None and (
        not math.isfinite(float(adjusted_entry_price)) or adjusted_entry_price <= 0.0
    ):
        raise ValueError("adjusted_entry_price must be finite and positive")
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
        adjusted_entry_price=(
            float(adjusted_entry_price) if adjusted_entry_price is not None else None
        ),
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
                "adjusted_entry_price": updated.adjusted_entry_price,
                "outcome_price": updated.outcome_price,
                "return_pct": updated.return_pct,
                "market_return_pct": updated.market_return_pct,
                "horizon_days": updated.horizon_days,
                "completed": completed,
            }
        )
    return pd.DataFrame(rows)


def attach_horizon_outcomes(
    records: list[SignalRecord],
    frames: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Attach outcomes only after the configured number of future trading bars.

    Frames may be keyed by ``EXCHANGE:SYMBOL`` (preferred) or by symbol. The
    signal timestamp is converted to the frame timezone before selecting bars.
    """
    rows = []
    for record in records:
        key = f"{record.exchange}:{record.symbol}"
        frame = frames.get(key, frames.get(record.symbol, pd.DataFrame()))
        outcome_price = None
        outcome_timestamp = None

        if frame is not None and not frame.empty:
            price_column = (
                "Adj Close"
                if record.adjusted_entry_price is not None and "Adj Close" in frame.columns
                else "Close"
            )
        else:
            price_column = "Close"
        if frame is not None and not frame.empty and price_column in frame.columns:
            close = pd.to_numeric(frame[price_column], errors="coerce")
            close = close.where(
                close.map(lambda value: pd.notna(value) and math.isfinite(float(value)))
            )
            close = close.where(close > 0).dropna().sort_index()
            close = close.loc[~close.index.duplicated(keep="last")]
            if isinstance(close.index, pd.DatetimeIndex):
                signal_time = pd.Timestamp(record.timestamp)
                if close.index.tz is None:
                    if signal_time.tzinfo is not None:
                        signal_time = signal_time.tz_convert("Asia/Kolkata").tz_localize(None)
                elif signal_time.tzinfo is None:
                    signal_time = signal_time.tz_localize(close.index.tz)
                else:
                    signal_time = signal_time.tz_convert(close.index.tz)
                # Yahoo daily bars are labelled by session date (often midnight),
                # not by the time their closing price became observable. Include
                # the signal date only when the signal predates the NSE/BSE close.
                session_dates = close.index.normalize()
                signal_date = signal_time.normalize()
                future_mask = session_dates > signal_date
                if signal_time.time() < time(15, 30):
                    future_mask |= session_dates == signal_date
                future = close.loc[future_mask]
                if len(future) >= record.horizon_days:
                    outcome_timestamp = future.index[record.horizon_days - 1]
                    outcome_price = float(future.iloc[record.horizon_days - 1])

        updated = SignalRecord(**{**record.__dict__, "outcome_price": outcome_price})
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
                "adjusted_entry_price": updated.adjusted_entry_price,
                "outcome_price": updated.outcome_price,
                "outcome_timestamp": outcome_timestamp,
                "return_pct": updated.return_pct,
                "market_return_pct": updated.market_return_pct,
                "horizon_days": updated.horizon_days,
                "completed": outcome_price is not None,
            }
        )
    return pd.DataFrame(rows)


def summarize_outcomes(history: pd.DataFrame) -> pd.DataFrame:
    """Summarize directional results separately from neutral market movement."""
    columns = [
        "signal",
        "signals",
        "completed",
        "evaluated",
        "win_rate_pct",
        "avg_return_pct",
        "market_avg_return_pct",
        "underlying_up_rate_pct",
    ]
    if history.empty:
        return pd.DataFrame(columns=columns)

    completed = history.loc[history["completed"].fillna(False)].copy()
    if completed.empty:
        return pd.DataFrame(columns=columns)

    if "market_return_pct" not in completed:
        completed["market_return_pct"] = pd.NA
    completed["return_pct"] = pd.to_numeric(completed["return_pct"], errors="coerce")
    completed["market_return_pct"] = pd.to_numeric(
        completed["market_return_pct"], errors="coerce"
    )

    rows = []
    for signal, group in completed.groupby("signal", sort=True):
        strategy_returns = group["return_pct"].dropna()
        market_returns = group["market_return_pct"].dropna()
        rows.append(
            {
                "signal": signal,
                "signals": len(group),
                "completed": int(group["completed"].sum()),
                "evaluated": len(strategy_returns),
                "win_rate_pct": (
                    float((strategy_returns > 0.0).mean() * 100.0)
                    if not strategy_returns.empty
                    else float("nan")
                ),
                "avg_return_pct": (
                    float(strategy_returns.mean())
                    if not strategy_returns.empty
                    else float("nan")
                ),
                "market_avg_return_pct": (
                    float(market_returns.mean()) if not market_returns.empty else float("nan")
                ),
                "underlying_up_rate_pct": (
                    float((market_returns > 0.0).mean() * 100.0)
                    if not market_returns.empty
                    else float("nan")
                ),
            }
        )
    return pd.DataFrame(rows, columns=columns)
