"""Measure how much of a ticker list the market-data provider actually returns.

"No BSE stocks" and "some BSE stocks" are different problems with different fixes, so the
Data Health page reports a coverage rate per ticker form (NSE names, BSE scrip codes, BSE
names) instead of one pass/fail. Pure: the downloader is passed in, so it is unit tested.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

import pandas as pd

from services.parallel_download import download_in_parallel

Downloader = Callable[..., tuple[dict[str, pd.DataFrame], list[str]]]

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
GOOD_RATE = 0.80
PARTIAL_RATE = 0.40


@dataclass(frozen=True)
class Coverage:
    label: str
    tested: int
    loaded: int
    missing: tuple[str, ...]

    @property
    def rate(self) -> float:
        return self.loaded / self.tested if self.tested else 0.0


def measure_coverage(
    label: str,
    tickers: Iterable[str],
    downloader: Downloader,
    *,
    chunk_size: int = 8,
    workers: int = 4,
    **kwargs,
) -> Coverage:
    """Download ``tickers`` and count the ones that came back with at least one row."""
    wanted = list(dict.fromkeys(str(t).strip().upper() for t in tickers if str(t).strip()))
    frames, _ = download_in_parallel(
        downloader, wanted, chunk_size=chunk_size, workers=workers, **kwargs
    )
    loaded = {t for t, frame in frames.items() if frame is not None and not frame.empty}
    return Coverage(
        label=label,
        tested=len(wanted),
        loaded=len(loaded),
        missing=tuple(t for t in wanted if t not in loaded),
    )


def verdict(coverage: Coverage) -> tuple[str, str]:
    """``(status, advice)`` for one coverage result."""
    if coverage.tested == 0:
        return WARN, "Nothing was tested."
    pct = f"{coverage.loaded}/{coverage.tested} ({coverage.rate:.0%})"
    if coverage.rate >= GOOD_RATE:
        return PASS, f"{pct} loaded. Scans on this list will look complete."
    if coverage.rate >= PARTIAL_RATE:
        return WARN, (
            f"Only {pct} loaded. Scans will silently cover part of the list; this is usually "
            "provider throttling, so retry in a few minutes or reduce the scan depth."
        )
    return FAIL, (
        f"Only {pct} loaded. The provider is not serving this list from this network. Check "
        "the connection, try again later, or use the other ticker form if it scores better."
    )


def best_form(results: list[Coverage]) -> str | None:
    """Label of the highest-coverage form when it beats the others by 10 points or more."""
    ranked = sorted(results, key=lambda c: c.rate, reverse=True)
    if len(ranked) < 2 or ranked[0].rate - ranked[1].rate < 0.10:
        return None
    return ranked[0].label
