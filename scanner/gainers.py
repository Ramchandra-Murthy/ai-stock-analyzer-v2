"""Compute intraday gainer rows from downloaded price frames (pure; no network, no Streamlit).

Extracted from the Personal Stock Watchlist page so the maths and, importantly, the
accounting of symbols that could not be scored can be unit tested. A symbol is never dropped
silently: every candidate ends up either in ``rows`` or in ``skipped`` with a reason.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field

import pandas as pd

from services.symbol_resolver import company_label


@dataclass(frozen=True)
class GainerScan:
    rows: list[dict] = field(default_factory=list)
    skipped: dict[str, str] = field(default_factory=dict)  # ticker -> reason
    candidates: int = 0

    @property
    def scored(self) -> int:
        return len(self.rows)


def _close(frames: Mapping[str, pd.DataFrame], ticker: str) -> pd.Series:
    frame = frames.get(ticker)
    if frame is None or "Close" not in frame:
        return pd.Series(dtype=float)
    return pd.to_numeric(frame["Close"], errors="coerce").dropna()


def build_gainer_rows(
    tickers: Iterable[str],
    intraday_frames: Mapping[str, pd.DataFrame],
    daily_frames: Mapping[str, pd.DataFrame],
    suffix: str,
) -> GainerScan:
    """Score each ticker by last price vs the previous daily close, sorted best first."""
    symbols = list(dict.fromkeys(tickers))
    rows: list[dict] = []
    skipped: dict[str, str] = {}
    for ticker in symbols:
        daily = _close(daily_frames, ticker)
        if daily.empty:
            skipped[ticker] = "no price data returned"
            continue
        if len(daily) < 2:
            skipped[ticker] = "fewer than two daily closes"
            continue
        previous = float(daily.iloc[-2])
        if previous <= 0:
            skipped[ticker] = "previous close is not positive"
            continue
        intraday = _close(intraday_frames, ticker)
        last = float(intraday.iloc[-1] if not intraday.empty else daily.iloc[-1])
        volume = pd.Series(dtype=float)
        frame = daily_frames.get(ticker)
        if frame is not None and "Volume" in frame:
            volume = pd.to_numeric(frame["Volume"], errors="coerce").dropna()
        rows.append(
            {
                "Symbol": ticker.removesuffix(suffix),
                "Company": company_label(ticker),
                "Ticker": ticker,
                "Price": last,
                "Change (%)": (last / previous - 1) * 100,
                "Volume": int(volume.iloc[-1]) if not volume.empty else None,
                "Market cap (₹)": None,
                "Cap segment": "Unverified",
            }
        )
    rows.sort(key=lambda row: row["Change (%)"], reverse=True)
    return GainerScan(rows=rows, skipped=skipped, candidates=len(symbols))


def coverage_message(scan: GainerScan, exchange: str, universe_size: int) -> str:
    """One honest sentence about how much of the universe was actually scored."""
    unscored = scan.candidates - scan.scored
    text = (
        f"Scored {scan.scored} of {scan.candidates} {exchange} candidates "
        f"(universe of {universe_size})."
    )
    if unscored:
        shown = ", ".join(company_label(t) for t in list(scan.skipped)[:6])
        more = f" and {len(scan.skipped) - 6} more" if len(scan.skipped) > 6 else ""
        text += f" {unscored} returned no usable data: {shown}{more}."
    return text


def download_with_fallback(
    download: Callable[[list[str]], tuple[dict[str, pd.DataFrame], list[str]]],
    tickers: Iterable[str],
    alternates: Mapping[str, str],
) -> dict[str, pd.DataFrame]:
    """Download ``tickers``; retry each one that came back empty under its alternate ticker.

    Yahoo serves some BSE listings under the scrip code (``500325.BO``) and others only under
    the name (``RELIANCE.BO``). A recovered frame is stored under the *original* ticker so the
    rest of the scan, and its coverage count, need no changes.
    """
    wanted = list(dict.fromkeys(tickers))
    frames, _ = download(wanted)
    frames = {t: f for t, f in frames.items() if f is not None and not f.empty}
    retry = {t: alternates[t] for t in wanted if t not in frames and alternates.get(t)}
    if retry:
        recovered, _ = download(list(dict.fromkeys(retry.values())))
        for original, alternate in retry.items():
            frame = recovered.get(alternate)
            if frame is not None and not frame.empty:
                frames[original] = frame
    return frames
