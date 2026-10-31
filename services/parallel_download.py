"""Run a chunked ticker download concurrently (pure; the downloader is passed in).

``download_symbol_frames`` fetches batches one after another, so scanning 80 BSE tickers with
a 4 second timeout can take minutes. That is why the BSE scan used to be cut to 8 symbols.
Splitting the list into chunks and running them on a small thread pool keeps the same
per-request timeout and retry behaviour but removes the serial wait.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pandas as pd

Downloader = Callable[..., tuple[dict[str, pd.DataFrame], list[str]]]


def download_in_parallel(
    downloader: Downloader,
    tickers: Iterable[str],
    *,
    chunk_size: int = 8,
    workers: int = 4,
    **kwargs: Any,
) -> tuple[dict[str, pd.DataFrame], list[str]]:
    """Return ``(frames, missing)`` merged across chunks; order of ``missing`` follows input.

    A chunk whose downloader raises is reported as missing rather than aborting the whole
    scan, so one bad batch cannot blank out every other symbol.
    """
    symbols = list(dict.fromkeys(str(t).strip().upper() for t in tickers if str(t).strip()))
    if not symbols:
        return {}, []
    size = max(1, int(chunk_size))
    chunks = [symbols[i : i + size] for i in range(0, len(symbols), size)]

    def run(chunk: list[str]) -> tuple[dict[str, pd.DataFrame], list[str]]:
        try:
            return downloader(chunk, **kwargs)
        except Exception:  # noqa: BLE001 - a provider failure must not abort the other chunks
            return {}, list(chunk)

    with ThreadPoolExecutor(max_workers=max(1, min(int(workers), len(chunks)))) as pool:
        results = list(pool.map(run, chunks))

    frames: dict[str, pd.DataFrame] = {}
    for part, _missing in results:
        frames.update(part)
    return frames, [t for t in symbols if t not in frames]
