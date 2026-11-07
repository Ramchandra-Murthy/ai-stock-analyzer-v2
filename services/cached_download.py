"""Short-lived, thread-safe cache around the Yahoo Finance downloader.

Concurrent callers for the same request share one in-flight download (single-flight).
Failures are propagated to all waiters but are never cached. Empty results have a short
TTL, returned frames are copied, and the completed cache is size-bounded.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterable
from concurrent.futures import Future
from typing import Any

import pandas as pd

DEFAULT_TTL_SECONDS = 900.0
EMPTY_TTL_SECONDS = 5.0
MAX_ENTRIES = 64

_Key = tuple[Any, ...]
_cache: dict[_Key, tuple[float, pd.DataFrame]] = {}
_inflight: dict[_Key, Future[pd.DataFrame]] = {}
_lock = threading.Lock()


def clear_download_cache() -> None:
    """Drop completed cache entries (in-flight requests are allowed to finish)."""
    with _lock:
        _cache.clear()


def cache_size() -> int:
    with _lock:
        return len(_cache)


def _default_downloader(*args: Any, **kwargs: Any) -> pd.DataFrame:
    import yfinance as yf

    return yf.download(*args, **kwargs)


def _make_key(
    tickers: str | Iterable[str],
    period: str,
    kwargs: dict[str, Any],
    downloader: Callable[..., pd.DataFrame],
) -> _Key:
    """Build a cache key that preserves ticker order and downloader identity."""
    symbols = tickers if isinstance(tickers, str) else tuple(tickers)
    return (
        symbols,
        period,
        tuple(sorted((key, repr(value)) for key, value in kwargs.items())),
        id(downloader),
    )


def _evict(now: float) -> None:
    """Remove expired entries, then the oldest ones until the cache is within bounds."""
    for key in [key for key, (expires, _) in _cache.items() if expires <= now]:
        del _cache[key]
    overflow = len(_cache) - MAX_ENTRIES
    if overflow > 0:
        oldest = sorted(_cache, key=lambda key: _cache[key][0])[:overflow]
        for key in oldest:
            del _cache[key]


def cached_download(
    tickers: str | Iterable[str],
    *,
    period: str,
    ttl: float = DEFAULT_TTL_SECONDS,
    cache_empty: bool = True,
    downloader: Callable[..., pd.DataFrame] | None = None,
    clock: Callable[[], float] = time.monotonic,
    **kwargs: Any,
) -> pd.DataFrame:
    """Run or reuse the Yahoo Finance download for the requested ticker set."""
    if isinstance(tickers, str):
        request: Any = tickers
    else:
        # Materialize iterables once: generators would otherwise be exhausted before keying.
        request = list(tickers)

    active_downloader = downloader or _default_downloader
    key = _make_key(request, period, kwargs, active_downloader)

    with _lock:
        now = clock()
        entry = _cache.get(key)
        if entry is not None and entry[0] > now:
            return entry[1].copy()

        pending = _inflight.get(key)
        is_owner = pending is None
        if is_owner:
            pending = Future()
            _inflight[key] = pending

    assert pending is not None
    if not is_owner:
        return pending.result().copy()

    try:
        frame = active_downloader(request, period=period, **kwargs)
        stored = pd.DataFrame() if frame is None else frame.copy()
        lifetime = (
            EMPTY_TTL_SECONDS
            if stored.empty and cache_empty
            else 0.0
            if stored.empty
            else max(0.0, ttl)
        )
        with _lock:
            completed_at = clock()
            _cache[key] = (completed_at + lifetime, stored.copy())
            _evict(completed_at)
            _inflight.pop(key, None)
        pending.set_result(stored.copy())
        return stored.copy()
    except BaseException as exc:
        with _lock:
            _inflight.pop(key, None)
        pending.set_exception(exc)
        raise
