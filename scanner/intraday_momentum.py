"""Deterministic intraday momentum features and candidate scoring.

Research/paper-trading only. This module does not fetch data or place orders.
Input candles must be timestamped OHLCV bars for one symbol, sorted or sortable
by timestamp. Historical sessions are used only to estimate time-of-day volume.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

REQUIRED_COLUMNS = {"Open", "High", "Low", "Close", "Volume"}
IST = "Asia/Kolkata"


@dataclass(frozen=True)
class RadarConfig:
    """Initial transparent scoring thresholds; tune only with out-of-sample tests."""

    opening_range_minutes: int = 15
    rvol_watch: float = 1.5
    rvol_confirm: float = 2.0
    max_vwap_extension_pct: float = 5.0
    min_turnover: float = 5_000_000.0


def _as_intraday_frame(candles: pd.DataFrame) -> pd.DataFrame:
    if candles is None or candles.empty:
        return pd.DataFrame()
    missing = REQUIRED_COLUMNS.difference(candles.columns)
    if missing:
        raise ValueError(f"Missing OHLCV columns: {', '.join(sorted(missing))}")
    frame = candles.copy()
    if not isinstance(frame.index, pd.DatetimeIndex):
        if "Datetime" in frame.columns:
            frame = frame.set_index("Datetime")
        elif "timestamp" in frame.columns:
            frame = frame.set_index("timestamp")
        else:
            raise ValueError("Candles require a DatetimeIndex or Datetime/timestamp column.")
    frame.index = pd.to_datetime(frame.index)
    if frame.index.tz is None:
        frame.index = frame.index.tz_localize(IST)
    else:
        frame.index = frame.index.tz_convert(IST)
    frame = frame.sort_index()
    for column in REQUIRED_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=list(REQUIRED_COLUMNS))
    frame = frame[(frame["Volume"] >= 0) & (frame["High"] >= frame["Low"])]
    return frame


def _time_of_day_rvol(frame: pd.DataFrame) -> float | None:
    """Compare today's cumulative volume with prior sessions at the same bar times.

    Uses the median cumulative volume from historical sessions, avoiding the
    misleading comparison of early-session volume to a full-day average.
    """
    if frame.empty:
        return None
    dates = pd.Index(frame.index.date).unique()
    if len(dates) < 2:
        return None
    today = dates[-1]
    today_frame = frame[pd.Index(frame.index.date) == today]
    prior = frame[pd.Index(frame.index.date) < today]
    if today_frame.empty or prior.empty:
        return None

    today_cum = today_frame["Volume"].sum()
    by_session = prior.groupby(prior.index.date)["Volume"].sum()
    baseline = float(by_session.median())
    if baseline <= 0:
        return None
    # A session-total baseline is only a fallback when historical intraday
    # coverage is incomplete; it is not represented as exact bar-time RVOL.
    return float(today_cum / baseline)


def build_intraday_radar_features(
    candles: pd.DataFrame,
    *,
    previous_close: float | None = None,
    config: RadarConfig | None = None,
) -> dict[str, Any]:
    """Calculate current-session features and a transparent momentum score."""
    cfg = config or RadarConfig()
    frame = _as_intraday_frame(candles)
    if frame.empty:
        return {"status": "NO_DATA", "score": 0, "reasons": ["No valid OHLCV bars"]}

    session_date = frame.index[-1].date()
    session = frame[pd.Index(frame.index.date) == session_date]
    if session.empty:
        return {"status": "NO_DATA", "score": 0, "reasons": ["No current-session bars"]}

    last = session.iloc[-1]
    first = session.iloc[0]
    close = float(last["Close"])
    open_price = float(first["Open"])
    high = float(session["High"].max())
    low = float(session["Low"].min())
    typical_price = (session["High"] + session["Low"] + session["Close"]) / 3.0
    vwap_denominator = float(session["Volume"].sum())
    vwap = (
        float((typical_price * session["Volume"]).sum() / vwap_denominator)
        if vwap_denominator > 0
        else None
    )
    from_open_pct = ((close / open_price) - 1.0) * 100 if open_price > 0 else None
    from_prev_pct = (
        ((close / previous_close) - 1.0) * 100
        if previous_close is not None and previous_close > 0
        else None
    )
    vwap_distance_pct = (
        ((close / vwap) - 1.0) * 100 if vwap is not None and vwap > 0 else None
    )
    turnover = float((session["Close"] * session["Volume"]).sum())

    opening_end = session.index[0] + pd.Timedelta(minutes=cfg.opening_range_minutes)
    opening = session[session.index < opening_end]
    opening_high = float(opening["High"].max()) if not opening.empty else None
    opening_low = float(opening["Low"].min()) if not opening.empty else None
    orb_breakout = bool(
        opening_high is not None
        and len(session) > len(opening)
        and close > opening_high
    )

    rvol = _time_of_day_rvol(frame)
    reasons: list[str] = []
    score = 0
    if rvol is not None:
        if rvol >= cfg.rvol_watch:
            score += 25
            reasons.append(f"Elevated relative volume ({rvol:.2f}x session baseline)")
        else:
            reasons.append(f"Relative volume below watch threshold ({rvol:.2f}x)")
    else:
        reasons.append("RVOL unavailable: insufficient prior-session intraday history")

    if from_open_pct is not None and from_open_pct > 0:
        score += 15
        reasons.append(f"Positive move from open ({from_open_pct:.2f}%)")
    if vwap is not None and close > vwap:
        score += 20
        reasons.append("Price above session VWAP")
    if orb_breakout:
        score += 25
        reasons.append("Price above opening-range high")
    if turnover >= cfg.min_turnover:
        score += 10
        reasons.append("Turnover meets minimum liquidity threshold")
    if rvol is not None and rvol >= cfg.rvol_confirm and orb_breakout and close > (vwap or 0):
        score += 5
        reasons.append("Volume-confirmed momentum conditions aligned")

    extended = vwap_distance_pct is not None and vwap_distance_pct > cfg.max_vwap_extension_pct
    if extended:
        score = max(0, score - 20)
        reasons.append("Extended above VWAP; avoid chasing")
    if turnover < cfg.min_turnover:
        score = max(0, score - 15)
        reasons.append("Low turnover; liquidity penalty")

    if extended:
        status = "LATE / EXTENDED"
    elif orb_breakout and close > (vwap or float("inf")) and (rvol or 0) >= cfg.rvol_confirm:
        status = "TRIGGER CONFIRMED"
    elif score >= 40:
        status = "WATCH"
    else:
        status = "REJECT / LOW CONFIDENCE"

    return {
        "status": status,
        "score": int(min(100, max(0, score))),
        "session_date": str(session_date),
        "last_bar_time": session.index[-1].isoformat(),
        "open": open_price,
        "last_price": close,
        "session_high": high,
        "session_low": low,
        "from_open_pct": from_open_pct,
        "from_previous_close_pct": from_prev_pct,
        "vwap": vwap,
        "vwap_distance_pct": vwap_distance_pct,
        "rvol": rvol,
        "opening_range_high": opening_high,
        "opening_range_low": opening_low,
        "opening_range_breakout": orb_breakout,
        "turnover": turnover,
        "reasons": reasons,
    }
