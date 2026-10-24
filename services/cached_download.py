"""Short-lived, thread-safe cache around ``yfinance.download``.

Streamlit pages re-run top to bottom on every interaction, and several pages downloaded the
same history again each time (a multi-second network call). Results are reused for ``ttl``
seconds. Rules that keep it safe:

* failures (exceptions) are never cached, so a transient error is retried on the next call;
* empty results are cached only very briefly, so a provider hiccup recovers quickly;
* callers always get a copy, so mutating a frame cannot corrupt the cache;
* the cache is size-bounded (oldest entries are evicted), so it cannot grow without limit;
* ``yfinance`` is imported lazily, keeping module import cheap.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterable
from typing import Any

import pandas as pd

DEFAULT_TTL_SECONDS = 900.0
EMPTY_TTL_SECONDS = 5.0
MAX_ENTRIES = 64

_Key = tuple[Any, ...]
_cache: dict[_Key, tuple[float, pd.DataFrame]] = {}
_lock = threading.Lock()


def clear_download_cache() -> None:
    """Drop every cached download (for a manual refresh and for tests)."""
    with _lock:
        _cache.clear()


def cache_size() -> int:
    with _lock:
        return len(_cache)


def _default_downloader(*args: Any, **kwargs: Any) -> pd.DataFrame:
    import yfinance as yf

    return yf.download(*args, **kwargs)


def _make_key(tickers: str | Iterable[str], period: str, kwargs: dict[str, Any]) -> _Key:
    # Ticker order is part of the key: yfinance orders columns by it, and callers rely on that.
    symbols = tickers if isinstance(tickers, str) else tuple(tickers)
    return (symbols, period, tuple(sorted((k, repr(v)) for k, v in kwargs.items())))


def _evict(now: float) -> None:
    """Remove expired entries, then the oldest ones until the cache is within bounds."""
    for key in [k for k, (expires, _) in _cache.items() if expires <= now]:
        del _cache[key]
    overflow = len(_cache) - MAX_ENTRIES
    if overflow > 0:
        for key in sorted(_cache, key=lambda k: _cache[k][0])[:overflow]:
            del _cache[key]


def cached_download(
    tickers: str | Iterable[str],
    *,
    period: str,
    ttl: float = DEFAULT_TTL_SECONDS,
    downloader: Callable[..., pd.DataFrame] | None = None,
    clock: Callable[[], float] = time.monotonic,
    **kwargs: Any,
) -> pd.DataFrame:
    """``yfinance.download(tickers, period=period, **kwargs)`` reused for ``ttl`` seconds."""
    if isinstance(tickers, str):
        request: Any = tickers
    else:
        request = list(tickers)
    key = _make_key(tickers, period, kwargs)

    now = clock()
    with _lock:
        entry = _cache.get(key)
    if entry is not None and entry[0] > now:
        return entry[1].copy()

    frame = (downloader or _default_downloader)(request, period=period, **kwargs)

    lifetime = EMPTY_TTL_SECONDS if frame is None or frame.empty else ttl
    stored = pd.DataFrame() if frame is None else frame
    with _lock:
        _cache[key] = (now + lifetime, stored.copy())
        _evict(now)
    return stored.copy()
