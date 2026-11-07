"""Shared market-data freshness helpers.

A batch download can return tickers whose last bar is days older than the rest of the
batch (halted, suspended or delisted names, or a provider serving cached data). Computing
a "latest vs previous close" move from such a bar and ranking it next to fresh tickers
presents stale data as current. These helpers detect that without a trading calendar by
comparing every ticker's last bar with the most recent session seen in the same batch.

Pure functions: no network, no provider imports, so they are cheap to unit test.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date

import pandas as pd


def last_bar_date(data: pd.Series | pd.DataFrame | None) -> date | None:
    """Calendar date of the last bar, or ``None`` when it cannot be determined.

    Returns ``None`` for empty input and for indexes that are not datetimes (for example
    a ``RangeIndex`` after ``reset_index``), rather than guessing a date.
    """
    if data is None or len(data) == 0:
        return None
    index = data.index
    if not isinstance(index, pd.DatetimeIndex):
        return None
    stamp = index[-1]
    if pd.isna(stamp):
        return None
    return pd.Timestamp(stamp).date()


def split_stale(
    last_dates: Mapping[str, date | None],
    *,
    today: date | None = None,
) -> tuple[date | None, list[str]]:
    """Return ``(reference_session, stale_tickers)`` for a batch of last-bar dates.

    The reference session is the most recent last-bar date in the batch, ignoring dates
    after ``today`` (a future-dated bar is invalid and must not mark everyone else stale).
    Any ticker whose last bar is older than the reference, or unknown, is stale.
    """
    valid = [d for d in last_dates.values() if d is not None and (today is None or d <= today)]
    if not valid:
        return None, sorted(last_dates)
    reference = max(valid)
    stale = [ticker for ticker, d in last_dates.items() if d is None or d != reference]
    return reference, sorted(stale)



def filter_stale_frames(
    frames: Mapping[str, pd.DataFrame],
    *,
    today: date | None = None,
) -> tuple[dict[str, pd.DataFrame], dict[str, object]]:
    """Keep only frames on the newest observed session in a batch.

    This relative guard catches halted or delayed symbols without assuming an
    exchange calendar. It does not claim that the whole batch is current; callers
    should describe the result as relative freshness, not exchange-live freshness.
    """
    last_dates = {symbol: last_bar_date(frame) for symbol, frame in frames.items()}
    reference, stale = split_stale(last_dates, today=today)
    stale_set = set(stale)
    usable = {symbol: frame for symbol, frame in frames.items() if symbol not in stale_set}
    return usable, {
        "reference_session": reference.isoformat() if reference is not None else None,
        "stale_symbols": stale,
        "checked_symbols": len(frames),
        "usable_symbols": len(usable),
        "policy": "relative_latest_session",
    }
