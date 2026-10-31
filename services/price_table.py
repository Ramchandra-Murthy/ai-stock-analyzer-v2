"""Download a wide close-price table for NSE and BSE tickers, naming every symbol with no data.

Several research pages each carried a private copy of "append .NS, download, rename columns".
Those copies could not take BSE tickers, and one empty ticker silently blanked the whole table.
This module has no Streamlit import and takes the download function as an argument, so it is
unit tested without a network.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

import pandas as pd

Fetch = Callable[..., pd.DataFrame | None]


def _default_fetch() -> Fetch:
    from services.cached_download import cached_download

    return cached_download


def load_close_prices(
    tickers_by_name: Mapping[str, str],
    period: str,
    *,
    fetch: Fetch | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """Return ``(close, missing)``: adjusted closes with one column per name, and the names
    that came back empty (so the caller can say which symbols failed instead of a bare error).

    ``tickers_by_name`` maps a display name to a full Yahoo ticker (``TCS.NS``, ``500325.BO``).
    """
    if not tickers_by_name:
        raise ValueError("No symbols to download.")
    ticker_to_name = {ticker: name for name, ticker in tickers_by_name.items()}
    if len(ticker_to_name) != len(tickers_by_name):
        raise ValueError("Two names point at the same ticker.")
    tickers = list(ticker_to_name)
    raw = (fetch or _default_fetch())(tickers, period=period, auto_adjust=True, progress=False)
    if raw is None or raw.empty:
        return pd.DataFrame(), list(tickers_by_name)

    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"]
    else:
        close = raw[["Close"]].copy()
        close.columns = tickers[:1]
    close = close.rename(columns=lambda c: ticker_to_name.get(str(c), str(c)))
    close = close.dropna(axis=1, how="all")
    missing = [name for name in tickers_by_name if name not in close.columns]
    return close.reindex(columns=[n for n in tickers_by_name if n in close.columns]), missing


def load_returns(
    tickers_by_name: Mapping[str, str],
    period: str,
    *,
    fetch: Fetch | None = None,
    min_rows: int = 60,
) -> tuple[pd.DataFrame, list[str]]:
    """Like :func:`load_close_prices` but returns daily returns on the dates every symbol that
    did load shares. Raises ``ValueError`` if nothing usable came back."""
    close, missing = load_close_prices(tickers_by_name, period, fetch=fetch)
    if close.empty:
        raise ValueError(
            "No price data came back for: " + ", ".join(missing) + ". Check the symbols or "
            "try again shortly."
        )
    returns = close.pct_change().dropna(how="any")
    if len(returns) < min_rows:
        raise ValueError(
            f"Only {len(returns)} shared trading days across the symbols that loaded; "
            "use a longer history or drop recently listed stocks."
        )
    return returns, missing
