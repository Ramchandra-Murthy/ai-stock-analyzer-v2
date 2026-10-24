"""Intraday opportunity screening for momentum and low-priced stocks.

The scanner ranks observable intraday conditions; it does not predict profits or
provide guaranteed trade signals. The candidate universe is the repository's
current NSE+BSE symbol list and is therefore not an exchange-wide screener.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import yfinance as yf

from scanner.day_trading_strategy import (
    analyze_day_trade_setup,
    calculate_day_trade_plan,
    classify_day_trade_plan_state,
)
from scanner.surveillance import (
    apply_safety_filter,
    fetch_nse_safety_snapshot,
    liquidity_warning,
)
from scanner.universe import BSE_CANDIDATES, NSE_CANDIDATES, bse_candidates_for_nse_symbols
from scanner.unusual_activity import CAP_UNIVERSES
from services.intraday_vwap_orb import vwap_orb_metrics

CHUNK_SIZE = 100
MAX_FAST_UNIVERSE = 200


def summarize_day_trading_setup(strategy: dict[str, Any]) -> dict[str, Any]:
    """Convert setup-engine conditions into concise scanner evidence."""
    long_score = strategy["Long setup score"]
    short_score = strategy["Short setup score"]
    direction = (
        "LONG" if long_score > short_score else "SHORT" if short_score > long_score else "NEUTRAL"
    )
    trend = strategy["Trend"]
    vwap_relation = strategy["VWAP relation"]
    ema_alignment = strategy["EMA 9/20"]
    rvol = strategy["RVOL"]
    breakout = strategy["Breakout"]
    breakdown = strategy["Breakdown"]

    evidence = []
    if trend != "MIXED":
        evidence.append(trend)
    if vwap_relation in {"ABOVE", "BELOW"}:
        evidence.append(f"VWAP {vwap_relation}")
    if ema_alignment in {"BULLISH", "BEARISH"}:
        evidence.append(f"EMA {ema_alignment}")
    if rvol >= 1.5:
        evidence.append("RVOL CONFIRMED")
    if breakout == "YES":
        evidence.append("BREAKOUT")
    if breakdown == "YES":
        evidence.append("BREAKDOWN")

    if direction == "LONG" and long_score >= 70:
        setup_state = "LONG SETUP WATCH"
    elif direction == "SHORT" and short_score >= 70:
        setup_state = "SHORT SETUP WATCH"
    else:
        setup_state = "CONTEXT ONLY"

    return {
        "Direction": direction,
        "Setup state": setup_state,
        "Evidence": " • ".join(evidence) if evidence else "No strong confirmation",
    }


def select_day_trader_universe(
    cap_category: str = "All caps",
    exchange_category: str = "Both",
) -> list[tuple[str, str]]:
    """Return the selected candidate universe, using live NSE/BSE lists for All caps."""
    if cap_category not in {"All caps", *CAP_UNIVERSES}:
        return []
    exchanges = ("NSE", "BSE") if exchange_category == "Both" else (exchange_category,)
    if cap_category == "All caps":
        # The live exchange lists can contain thousands of symbols. Downloading
        # 1-minute candles for that entire universe makes the interactive scanner
        # too slow. Use the maintained curated universe for the fast broad scan;
        # the detailed setup engine still evaluates every symbol that passes the
        # cheap first-stage filters.
        universe = [(symbol, "NSE") for symbol in NSE_CANDIDATES] + [
            (symbol, "BSE") for symbol in BSE_CANDIDATES
        ]
    else:
        selected = CAP_UNIVERSES[cap_category]
        universe = [(symbol, "NSE") for symbol in NSE_CANDIDATES if symbol in selected]
        universe.extend((symbol, "BSE") for symbol in bse_candidates_for_nse_symbols(selected))
    filtered = [(symbol, venue) for symbol, venue in universe if venue in exchanges]
    return filtered[:MAX_FAST_UNIVERSE]


def _candle_settings(lookback_minutes: int) -> tuple[str, int]:
    """Use the smallest candle interval that supports the requested lookback."""
    if lookback_minutes in (2, 3):
        candle_minutes = 1
    else:
        candle_minutes = 5
    interval = f"{candle_minutes}m"
    bars = max(1, int(round(lookback_minutes / candle_minutes)))
    return interval, bars


def _ticker(symbol: str, exchange: str) -> str:
    cleaned = str(symbol).strip().upper()
    suffix = ".NS" if exchange == "NSE" else ".BO"
    return cleaned if cleaned.endswith((".NS", ".BO")) else f"{cleaned}{suffix}"


def _frame(history: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if history is None or history.empty:
        return pd.DataFrame()
    if isinstance(history.columns, pd.MultiIndex):
        if ticker not in history.columns.get_level_values(0):
            return pd.DataFrame()
        data = history[ticker].copy()
    else:
        data = history.copy()
    required = {"High", "Low", "Close", "Volume"}
    if not required.issubset(data.columns):
        return pd.DataFrame()
    data = data.dropna(subset=list(required)).sort_index()
    return data[~data.index.duplicated(keep="last")]


def score_opportunity_rows(rows: pd.DataFrame) -> pd.DataFrame:
    """Score observable momentum, volume, range, and breakout conditions."""
    if rows is None or rows.empty:
        return pd.DataFrame()

    result = rows.copy()
    momentum = (result["5-min change %"].clip(lower=0) / 2.0 * 35).clip(upper=35)
    volume = ((result["Volume surge x"] - 1.0).clip(lower=0) / 2.0 * 30).clip(upper=30)
    volatility = (result["Session range %"].clip(lower=0) / 4.0 * 20).clip(upper=20)
    breakout = result["Breakout"].eq("YES").astype(float) * 15
    result["Opportunity score"] = (momentum + volume + volatility + breakout).round(1)

    setup_score = result.get("Setup score", result["Opportunity score"])
    result["Composite score"] = (result["Opportunity score"] * 0.6 + setup_score * 0.4).round(1)

    result["Setup"] = "Momentum watch"
    result.loc[
        (result["Volume surge x"] >= 1.5) & (result["5-min change %"] >= 0.75),
        "Setup",
    ] = "Volume + momentum"
    result.loc[result["Breakout"].eq("YES"), "Setup"] = "Breakout watch"
    result.loc[
        result["Low-price flag"].eq("YES") & (result["Volume surge x"] >= 1.5),
        "Setup",
    ] = "Low-price volume watch"

    return result.sort_values(
        ["Composite score", "Opportunity score", "5-min change %", "Volume surge x"],
        ascending=[False, False, False, False],
        na_position="last",
    ).reset_index(drop=True)


def scan_day_trader_opportunities(
    limit: int = 20,
    exchange_category: str = "Both",
    cap_category: str = "All caps",
    max_price: float = 50.0,
    lookback_minutes: int = 5,
    min_change_percent: float = 0.5,
    min_volume_surge: float = 1.2,
    low_price_only: bool = False,
) -> pd.DataFrame:
    """Find intraday momentum candidates, including configurable low-price mode.

    max_price is a configurable low-price threshold, not a formal definition
    of a penny stock. Prices and eligibility use the latest Yahoo Finance
    candle returned by the provider.
    """
    if (
        limit < 1
        or max_price <= 0
        or lookback_minutes not in (2, 3, 5)
        or min_change_percent < 0
        or min_volume_surge < 0
        or cap_category not in {"All caps", *CAP_UNIVERSES}
    ):
        return pd.DataFrame()

    universe = select_day_trader_universe(cap_category, exchange_category)
    exchanges = ("NSE", "BSE") if exchange_category == "Both" else (exchange_category,)

    # Use 5-minute candles for the default 5-minute scan. This cuts the Yahoo
    # payload substantially while preserving the requested 5-minute signal.
    # The 2- and 3-minute modes retain 1-minute candles for finer timing.
    interval, bars = _candle_settings(lookback_minutes)
    candle_minutes = 1 if interval == "1m" else 5
    rows: list[dict[str, Any]] = []
    scan_stats: dict[str, Any] = {
        "candidate_count": len(universe),
        "attempted_count": 0,
        "usable_data_count": 0,
        "strategy_count": 0,
        "download_failed_chunks": 0,
        "empty_chunks": 0,
        "filtered_count": 0,
        "price_change_pass_count": 0,
        "volume_surge_pass_count": 0,
        "both_filters_pass_count": 0,
        "low_price_pass_count": 0,
        "matches_before_safety": 0,
        "matches_after_safety": 0,
        "interval": interval,
        "lookback_minutes": lookback_minutes,
        "exchange": exchange_category,
        "cap_category": cap_category,
    }

    for exchange in exchanges:
        tickers = [_ticker(symbol, exchange) for symbol, venue in universe if venue == exchange]
        for start in range(0, len(tickers), CHUNK_SIZE):
            chunk = tickers[start : start + CHUNK_SIZE]
            scan_stats["attempted_count"] += len(chunk)
            try:
                history = yf.download(
                    tickers=chunk,
                    period="1d",
                    interval=interval,
                    progress=False,
                    auto_adjust=False,
                    group_by="ticker",
                    threads=True,
                    timeout=10,
                )
            except Exception:
                scan_stats["download_failed_chunks"] += 1
                continue

            if history is None or history.empty:
                scan_stats["empty_chunks"] += 1
                continue

            for ticker in chunk:
                try:
                    data = _frame(history, ticker)
                    if len(data) <= bars:
                        continue

                    session_date = data.index[-1].date()
                    session = data.loc[[stamp.date() == session_date for stamp in data.index]]
                    close = pd.to_numeric(session["Close"], errors="coerce").dropna()
                    high = pd.to_numeric(session["High"], errors="coerce").dropna()
                    volume = pd.to_numeric(session["Volume"], errors="coerce").dropna()
                    if len(close) <= bars or len(volume) < 6:
                        continue

                    scan_stats["usable_data_count"] += 1
                    price = float(close.iloc[-1])
                    prior = float(close.iloc[-1 - bars])
                    if price <= 0 or prior <= 0:
                        continue

                    change = (price / prior - 1.0) * 100.0
                    baseline = float(volume.iloc[-min(21, len(volume) - 1) : -1].median())
                    latest_volume = float(volume.iloc[-1])
                    volume_surge = latest_volume / baseline if baseline > 0 else 0.0

                    session_high = float(pd.to_numeric(session["High"], errors="coerce").max())
                    session_low = float(pd.to_numeric(session["Low"], errors="coerce").min())
                    session_range = (
                        (session_high - session_low) / price * 100.0 if price > 0 else 0.0
                    )

                    prior_highs = high.iloc[-21:-1] if len(high) >= 21 else high.iloc[:-1]
                    breakout = len(prior_highs) > 0 and price > float(prior_highs.max())

                    price_pass = change >= min_change_percent
                    volume_pass = volume_surge >= min_volume_surge
                    if price_pass:
                        scan_stats["price_change_pass_count"] += 1
                    if volume_pass:
                        scan_stats["volume_surge_pass_count"] += 1
                    if price_pass and volume_pass:
                        scan_stats["both_filters_pass_count"] += 1

                    low_price = price <= max_price
                    if low_price:
                        scan_stats["low_price_pass_count"] += 1

                    # Cheap first-stage filters: avoid expensive strategy/VWAP
                    # calculations for symbols that cannot enter the result set.
                    if not price_pass or not volume_pass:
                        continue
                    if low_price_only and not low_price:
                        continue

                    strategy = analyze_day_trade_setup(
                        session,
                        opening_range_bars=5 if candle_minutes == 1 else 1,
                        level_lookback=min(20, max(5, len(session) - 1)),
                    )
                    if not strategy:
                        continue

                    scan_stats["strategy_count"] += 1
                    vwap_orb = vwap_orb_metrics(session, orb_minutes=(5, 15))
                    strategy.update(vwap_orb)

                    setup_score = max(
                        strategy["Long setup score"],
                        strategy["Short setup score"],
                    )
                    strategy_name = strategy["Setup"]
                    trend = strategy["Trend"]
                    vwap_relation = strategy["VWAP relation"]
                    ema_alignment = strategy["EMA 9/20"]
                    strategy_rvol = strategy["RVOL"]
                    strategy_breakout = strategy["Breakout"]
                    strategy_breakdown = strategy["Breakdown"]
                    orb_high = strategy["ORB high"]
                    orb_low = strategy["ORB low"]
                    strategy_summary = summarize_day_trading_setup(strategy)
                    trade_plan = calculate_day_trade_plan(strategy)
                    plan_state = classify_day_trade_plan_state(strategy, trade_plan)
                    direction = strategy_summary["Direction"]
                    setup_state = strategy_summary["Setup state"]
                    evidence_text = strategy_summary["Evidence"]

                    low_price = price <= max_price
                    if low_price:
                        scan_stats["low_price_pass_count"] += 1

                    if not price_pass or not volume_pass:
                        continue
                    if low_price_only and not low_price:
                        continue

                    rows.append(
                        {
                            "Symbol": ticker.rsplit(".", 1)[0],
                            "Exchange": exchange,
                            "Market-cap basket": cap_category,
                            "Price": round(price, 2),
                            "5-min change %": round(change, 2),
                            "Volume surge x": round(volume_surge, 2),
                            "Session range %": round(session_range, 2),
                            "Breakout": "YES" if breakout else "—",
                            "Day-trading setup": strategy_name,
                            "Direction": direction,
                            "Setup state": setup_state,
                            "Evidence": evidence_text,
                            "Plan": trade_plan["Plan"],
                            "Plan state": plan_state,
                            "Entry reference": trade_plan["Entry reference"],
                            "Stop reference": trade_plan["Stop reference"],
                            "Target 1": trade_plan["Target 1"],
                            "Target 2": trade_plan["Target 2"],
                            "Target 3": trade_plan["Target 3"],
                            "Risk per share": trade_plan["Risk per share"],
                            "R:R T1": trade_plan["R:R T1"],
                            "R:R T2": trade_plan["R:R T2"],
                            "R:R T3": trade_plan["R:R T3"],
                            "Setup score": setup_score,
                            "Trend": trend,
                            "VWAP": vwap_relation,
                            "VWAP price": vwap_orb.get("VWAP"),
                            "VWAP distance %": vwap_orb.get("VWAP distance %"),
                            "VWAP bias": vwap_orb.get("VWAP bias"),
                            "ORB 5m high": vwap_orb.get("ORB 5m high"),
                            "ORB 5m low": vwap_orb.get("ORB 5m low"),
                            "ORB 5m state": vwap_orb.get("ORB 5m state"),
                            "ORB 15m high": vwap_orb.get("ORB 15m high"),
                            "ORB 15m low": vwap_orb.get("ORB 15m low"),
                            "ORB 15m state": vwap_orb.get("ORB 15m state"),
                            "EMA 9/20": ema_alignment,
                            "RVOL": strategy_rvol,
                            "ORB high": orb_high,
                            "ORB low": orb_low,
                            "Strategy breakout": strategy_breakout,
                            "Strategy breakdown": strategy_breakdown,
                            "Low-price flag": "YES" if low_price else "—",
                            "Latest candle": str(session.index[-1]),
                            "Data delay": "15 min" if exchange == "BSE" else "Real-time",
                            "Liquidity": liquidity_warning(price, latest_volume),
                        }
                    )
                except (KeyError, TypeError, ValueError, IndexError):
                    continue

    if not rows:
        empty = pd.DataFrame()
        empty.attrs["scan_stats"] = scan_stats
        return empty

    result = pd.DataFrame(rows)
    scan_stats["matches_before_safety"] = len(result)
    result = score_opportunity_rows(result)
    result["Screen"] = result["Low-price flag"].map(
        {"YES": f"Low-price <= ₹{max_price:g}", "—": "Momentum"}
    )

    nse_symbols = result.loc[result["Exchange"].eq("NSE"), "Symbol"].tolist()
    safety, _ = fetch_nse_safety_snapshot(nse_symbols)
    result = apply_safety_filter(result, safety, exclude_flagged=False)
    scan_stats["matches_after_safety"] = len(result)
    scan_stats["filtered_count"] = max(
        0,
        scan_stats["usable_data_count"] - scan_stats["matches_before_safety"],
    )
    result = result.head(max(1, min(int(limit), 100))).reset_index(drop=True)
    scan_stats["displayed_count"] = len(result)
    result.attrs["scan_stats"] = scan_stats
    return result
