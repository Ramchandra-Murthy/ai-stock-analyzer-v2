"""Turn per-article scores into daily series, decayed snapshots, features and a signal."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _naive_utc(ts: pd.Series) -> pd.Series:
    out = pd.to_datetime(ts, utc=True, errors="coerce")
    return out.dt.tz_convert("UTC").dt.tz_localize(None)


def daily_sentiment(scored: pd.DataFrame) -> pd.DataFrame:
    """Average article scores per UTC calendar day.

    Returns a frame indexed by date with ``score`` (mean) and ``n_articles``.
    Articles without a parseable date are dropped.
    """
    empty = pd.DataFrame(columns=["score", "n_articles"], index=pd.DatetimeIndex([], name="date"))
    if scored.empty or "published" not in scored.columns:
        return empty
    ts = _naive_utc(scored["published"])
    frame = pd.DataFrame({"date": ts.dt.normalize(), "score": scored["score"].astype(float)})
    frame = frame.dropna()
    if frame.empty:
        return empty
    grouped = frame.groupby("date")["score"].agg(score="mean", n_articles="count")
    grouped.index.name = "date"
    return grouped.sort_index()


def decayed_sentiment(
    scored: pd.DataFrame,
    asof: pd.Timestamp | None = None,
    half_life_days: float = 3.0,
) -> dict[str, float]:
    """Exponentially time-decayed mean sentiment using only articles published <= ``asof``.

    Point-in-time safe: later articles never leak into an earlier snapshot.
    """
    result = {"score": 0.0, "n": 0.0, "effective_n": 0.0}
    if scored.empty or half_life_days <= 0:
        return result
    ts = _naive_utc(scored["published"])
    cutoff = pd.Timestamp.utcnow().tz_localize(None) if asof is None else pd.Timestamp(asof)
    if cutoff.tzinfo is not None:
        cutoff = cutoff.tz_convert("UTC").tz_localize(None)
    age_days = (cutoff - ts).dt.total_seconds() / 86400.0
    mask = age_days.notna() & (age_days >= 0)
    if not mask.any():
        return result
    weights = np.power(0.5, age_days[mask].to_numpy() / half_life_days)
    scores = scored.loc[mask, "score"].astype(float).to_numpy()
    wsum = float(weights.sum())
    return {
        "score": round(float((weights * scores).sum() / wsum), 4),
        "n": float(mask.sum()),
        "effective_n": round(wsum**2 / float((weights**2).sum()), 2),
    }


def sentiment_features(
    daily: pd.DataFrame,
    span: int = 5,
    z_window: int = 20,
) -> pd.DataFrame:
    """Rolling features on a daily sentiment frame (see :func:`daily_sentiment`).

    Columns: ``score`` (raw, NaN on no-news days), ``ewm`` (smoothed level),
    ``momentum`` (ewm change over ``span`` days), ``zscore`` (ewm vs trailing
    ``z_window`` mean/std, using only past data) and ``volume_ratio`` (article count
    vs trailing mean). All use data up to and including each date only.
    """
    cols = ["score", "ewm", "momentum", "zscore", "volume_ratio"]
    if daily.empty:
        return pd.DataFrame(columns=cols)
    idx = pd.date_range(daily.index.min(), daily.index.max(), freq="D")
    d = daily.reindex(idx)
    count = d["n_articles"].fillna(0.0)
    ewm = d["score"].ewm(span=span, ignore_na=True, adjust=False).mean()
    roll = ewm.rolling(z_window, min_periods=max(5, z_window // 4))
    std = roll.std().replace(0.0, np.nan)
    trailing_count = count.rolling(z_window, min_periods=1).mean().replace(0.0, np.nan)
    return pd.DataFrame(
        {
            "score": d["score"],
            "ewm": ewm,
            "momentum": ewm - ewm.shift(span),
            "zscore": (ewm - roll.mean()) / std,
            "volume_ratio": count / trailing_count,
        }
    )


def sentiment_signal(
    score: float,
    n_articles: float,
    *,
    min_articles: int = 3,
    shrink_k: float = 3.0,
    threshold: float = 0.25,
) -> dict[str, float | str]:
    """Map a sentiment level to a research label, shrunk toward 0 when evidence is thin.

    ``shrunk = score * n / (n + shrink_k)``. Fewer than ``min_articles`` returns
    ``INSUFFICIENT_DATA`` rather than a directional call. This is a screening label,
    not a trade instruction.
    """
    if n_articles is None or not math.isfinite(n_articles) or n_articles < min_articles:
        return {"label": "INSUFFICIENT_DATA", "shrunk_score": 0.0, "n": float(n_articles or 0)}
    shrunk = float(score) * n_articles / (n_articles + shrink_k)
    label = "BULLISH" if shrunk >= threshold else "BEARISH" if shrunk <= -threshold else "NEUTRAL"
    return {"label": label, "shrunk_score": round(shrunk, 4), "n": float(n_articles)}
