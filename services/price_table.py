"""Download a wide close-price table for NSE and BSE tickers, naming every symbol with no data.

Several research pages each carried a private copy of "append .NS, download, rename columns".
Those copies could not take BSE tickers, and one empty ticker silently blanked the whole table.
This module has no Streamlit import and takes the download function as an argument, so it is
unit tested without a network.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

import pandas as pd

from services.symbol_resolver import yahoo_ticker

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
    if len(set(tickers_by_name.values())) != len(tickers_by_name):
        raise ValueError("Two names point at the same ticker.")
    download = fetch or _default_fetch()

    # Ask Yahoo for the form it serves (BSE name rather than scrip code), then retry any
    # symbol that came back empty under the ticker the caller originally gave.
    preferred = {name: yahoo_ticker(ticker) for name, ticker in tickers_by_name.items()}
    close = _close_table(preferred, period, download)
    missing = [name for name in tickers_by_name if name not in close.columns]
    retry = {n: tickers_by_name[n] for n in missing if preferred[n] != tickers_by_name[n].upper()}
    if retry:
        extra = _close_table(retry, period, download)
        if not extra.empty:
            close = pd.concat([close, extra], axis=1)
            missing = [name for name in tickers_by_name if name not in close.columns]
    if close.empty:
        return pd.DataFrame(), missing
    return close.reindex(columns=[n for n in tickers_by_name if n in close.columns]), missing


def _close_table(by_name: Mapping[str, str], period: str, download: Fetch) -> pd.DataFrame:
    """One download; columns renamed to display names, empty columns dropped."""
    ticker_to_name = {ticker: name for name, ticker in by_name.items()}
    tickers = list(ticker_to_name)
    raw = download(tickers, period=period, auto_adjust=True, progress=False)
    if raw is None or raw.empty:
        return pd.DataFrame()
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"]
    else:
        close = raw[["Close"]].copy()
        close.columns = tickers[:1]
    close = close.rename(columns=lambda c: ticker_to_name.get(str(c), str(c)))
    return close.dropna(axis=1, how="all")


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
