"""Does sentiment predict returns? Lag-safe information coefficient and bucket returns.

Sentiment dated ``d`` is attached to the first trading day on or after ``d`` and then
lagged by ``lag`` further trading days, so the forward return starts strictly after the
news could have been known. Be sceptical of results on short histories: Yahoo-style
news feeds only expose recent articles, so build up your own dated archive first.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _align(daily_score: pd.Series, close: pd.Series, horizon: int, lag: int) -> pd.DataFrame:
    close = close.dropna().astype(float)
    close.index = pd.to_datetime(close.index).tz_localize(None)
    close = close[~close.index.duplicated()].sort_index()
    sent = daily_score.dropna().astype(float)
    sent.index = pd.to_datetime(sent.index).tz_localize(None)
    if close.empty or sent.empty:
        return pd.DataFrame(columns=["score", "fwd_return"])
    pos = close.index.searchsorted(sent.index, side="left")
    valid = pos < len(close)
    on_trading_day = (
        pd.Series(sent.to_numpy()[valid], index=close.index[pos[valid]]).groupby(level=0).mean()
    )
    fwd = close.shift(-(lag + horizon)) / close.shift(-lag) - 1.0
    return pd.DataFrame({"score": on_trading_day, "fwd_return": fwd}).dropna()


def information_coefficient(
    daily_score: pd.Series,
    close: pd.Series,
    horizon: int = 5,
    lag: int = 1,
    min_obs: int = 20,
) -> dict[str, float]:
    """Spearman rank correlation of sentiment with the next ``horizon``-day return.

    Returns ``ic``, ``t_stat`` (naive: overlapping returns inflate it when horizon > 1),
    ``n`` and ``hit_rate`` (share of days where sign(score) matched sign(return)).
    Values are NaN when fewer than ``min_obs`` aligned observations exist.
    """
    nan = {"ic": math.nan, "t_stat": math.nan, "n": 0.0, "hit_rate": math.nan}
    if horizon < 1 or lag < 0:
        raise ValueError("horizon must be >= 1 and lag >= 0")
    data = _align(daily_score, close, horizon, lag)
    n = len(data)
    if n < min_obs or data["score"].nunique() < 2:
        return {**nan, "n": float(n)}
    ic = float(data["score"].corr(data["fwd_return"], method="spearman"))
    if not math.isfinite(ic):
        return {**nan, "n": float(n)}
    t_stat = ic * math.sqrt((n - 2) / max(1e-12, 1 - ic * ic))
    nonzero = data[data["score"] != 0]
    hit = (
        float((np.sign(nonzero["score"]) == np.sign(nonzero["fwd_return"])).mean())
        if len(nonzero)
        else math.nan
    )
    return {
        "ic": round(ic, 4),
        "t_stat": round(t_stat, 3),
        "n": float(n),
        "hit_rate": round(hit, 4),
    }


def quantile_forward_returns(
    daily_score: pd.Series,
    close: pd.Series,
    horizon: int = 5,
    lag: int = 1,
    buckets: int = 3,
) -> pd.DataFrame:
    """Mean forward return by sentiment bucket (low -> high). Empty if too little data."""
    data = _align(daily_score, close, horizon, lag)
    if len(data) < buckets * 5 or data["score"].nunique() < buckets:
        return pd.DataFrame(columns=["bucket", "mean_fwd_return", "n"])
    data["bucket"] = pd.qcut(data["score"].rank(method="first"), buckets, labels=False) + 1
    out = data.groupby("bucket")["fwd_return"].agg(mean_fwd_return="mean", n="count").reset_index()
    return out
