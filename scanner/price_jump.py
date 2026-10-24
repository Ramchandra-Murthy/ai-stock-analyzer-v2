from __future__ import annotations

import pandas as pd

from scanner.universe import BSE_CANDIDATES, NSE_CANDIDATES, bse_candidates_for_nse_symbols
from scanner.unusual_activity import CAP_UNIVERSES, _ticker, finalize_scan_result
from services.resilient_market_data import download_market_frames

INTRADAY_PERIOD = "1d"
MAX_FAST_UNIVERSE = 200


def calculate_price_jump(
    frame: pd.DataFrame,
    lookback_bars: int = 1,
    jump_percent: float = 1.0,
) -> dict[str, float | None] | None:
    """Calculate the latest same-session price jump, day change and relative volume."""
    if frame is None or frame.empty or lookback_bars < 1:
        return None
    required = {"Close", "Volume"}
    if not required.issubset(frame.columns):
        return None

    clean = frame.loc[:, ["Close", "Volume"]].dropna().sort_index()
    clean = clean[~clean.index.duplicated(keep="last")]
    if clean.empty:
        return None

    session_date = clean.index[-1].date()
    current = clean.loc[clean.index.date == session_date]
    if len(current) <= lookback_bars:
        return None

    price = float(current.iloc[-1]["Close"])
    prior_price = float(current.iloc[-1 - lookback_bars]["Close"])
    session_open = float(current.iloc[0]["Close"])
    if price <= 0 or prior_price <= 0 or session_open <= 0:
        return None

    intraday_pct = (price / prior_price - 1.0) * 100.0
    day_pct = (price / session_open - 1.0) * 100.0
    baseline = float(current["Volume"].iloc[-min(13, len(current) - 1) : -1].mean())
    volume = float(current.iloc[-1]["Volume"])
    relative_volume = volume / baseline if baseline > 0 else float("nan")
    return {
        "price": price,
        "intraday_pct": round(intraday_pct, 10),
        "day_pct": round(day_pct, 10),
        "volume": volume,
        "relative_volume": relative_volume,
        "qualifies": float(intraday_pct >= jump_percent),
    }


def _candle_settings(lookback_minutes: int) -> tuple[str, int]:
    """Return the Yahoo interval and bar count for a minute lookback."""
    candle_minutes = 1 if lookback_minutes in (1, 2, 3) else 5
    interval = f"{candle_minutes}m"
    bars = max(1, int(round(lookback_minutes / candle_minutes)))
    return interval, bars


def _selected_price_jump_universe(
    cap_category: str,
    exchange_category: str,
) -> list[tuple[str, str]]:
    """Build the bounded candidate universe used by the interactive price pulse."""
    exchanges = ("NSE", "BSE") if exchange_category == "Both" else (exchange_category,)
    if cap_category == "All caps":
        universe = [(symbol, "NSE") for symbol in NSE_CANDIDATES] + [
            (symbol, "BSE") for symbol in BSE_CANDIDATES
        ]
    else:
        selected = CAP_UNIVERSES.get(cap_category, set())
        universe = [(symbol, "NSE") for symbol in NSE_CANDIDATES if symbol in selected]
        universe.extend((symbol, "BSE") for symbol in bse_candidates_for_nse_symbols(selected))
    filtered = [(symbol, venue) for symbol, venue in universe if venue in exchanges]
    unique = list(dict.fromkeys(filtered))
    return unique[:MAX_FAST_UNIVERSE]


def _append_price_jump_rows(
    rows: list[dict[str, object]],
    stats: dict[str, object],
    tickers: list[str],
    exchange: str,
    cap_category: str,
    lookback_minutes: int,
    bars: int,
    jump_percent: float,
    frames: dict[str, pd.DataFrame],
) -> None:
    """Append qualifying price-pulse rows and update scan diagnostics."""
    for ticker in tickers:
        try:
            frame = frames.get(ticker, pd.DataFrame())
            metrics = calculate_price_jump(frame, bars, jump_percent)
            if metrics is None:
                continue
            stats["usable_count"] = int(stats["usable_count"]) + 1
            if not bool(metrics["qualifies"]):
                continue
            rows.append(
                {
                    "Symbol": ticker.rsplit(".", 1)[0],
                    "Exchange": exchange,
                    "Market-cap basket": cap_category,
                    "Last price": round(float(metrics["price"]), 2),
                    f"Change over {lookback_minutes} min %": round(
                        float(metrics["intraday_pct"]), 2
                    ),
                    "Day %": round(float(metrics["day_pct"]), 2),
                    "Latest bar volume": int(metrics["volume"]),
                    "RVOL": (
                        round(float(metrics["relative_volume"]), 2)
                        if pd.notna(metrics["relative_volume"])
                        else None
                    ),
                    "Latest candle (provider time)": str(frame.index[-1]),
                }
            )
        except (KeyError, TypeError, ValueError, IndexError):
            stats["processing_errors"] = int(stats["processing_errors"]) + 1


def scan_price_jumps(
    limit: int = 20,
    cap_category: str = "All caps",
    exchange_category: str = "Both",
    lookback_minutes: int = 5,
    jump_percent: float = 1.0,
) -> pd.DataFrame:
    """Return stocks meeting the selected intraday price-jump threshold."""
    if (
        limit < 1
        or lookback_minutes < 1
        or jump_percent < 0
        or exchange_category not in {"NSE", "BSE", "Both"}
        or cap_category not in {"All caps", *CAP_UNIVERSES}
    ):
        return pd.DataFrame()

    selected_universe = _selected_price_jump_universe(cap_category, exchange_category)
    interval, bars = _candle_settings(lookback_minutes)
    duplicate_count = 0
    stats: dict[str, object] = {
        "candidate_count": len(selected_universe),
        "duplicate_candidates_removed": duplicate_count,
        "attempted_count": 0,
        "usable_count": 0,
        "download_failed_chunks": 0,
        "empty_chunks": 0,
        "processing_errors": 0,
        "matches_before_limit": 0,
        "displayed_count": 0,
        "interval": interval,
    }
    rows: list[dict[str, object]] = []

    exchanges = ("NSE", "BSE") if exchange_category == "Both" else (exchange_category,)
    for exchange in exchanges:
        tickers = [
            _ticker(symbol, exchange) for symbol, venue in selected_universe if venue == exchange
        ]
        stats["attempted_count"] = int(stats["attempted_count"]) + len(tickers)
        frames, diagnostics = download_market_frames(
            tickers,
            period=INTRADAY_PERIOD,
            interval=interval,
            batch_size=100,
            timeout=5,
            retries=0,
            recover_missing=False,
        )
        stats["download_failed_chunks"] = int(stats["download_failed_chunks"]) + int(
            bool(diagnostics["missing"])
        )
        stats["empty_chunks"] = int(stats["empty_chunks"]) + int(not frames and tickers)
        _append_price_jump_rows(
            rows,
            stats,
            tickers,
            exchange,
            cap_category,
            lookback_minutes,
            bars,
            jump_percent,
            frames,
        )

    return finalize_scan_result(
        rows,
        limit,
        [f"Change over {lookback_minutes} min %", "RVOL"],
        stats,
    )
