"""Text-input parsing for the Advanced Portfolio Lab page (pure functions, no Streamlit).

Kept separate from the page so the parsing rules can be unit tested.
"""

from __future__ import annotations

import math

from algorithmic_trading.portfolio_advanced import View
from services.symbol_resolver import company_label, resolve_symbol


def parse_holdings(raw: str) -> dict[str, float]:
    """Parse ``SYMBOL weight`` lines (commas allowed) into upper-case symbol -> weight."""
    out: dict[str, float] = {}
    for line in raw.splitlines():
        parts = line.replace(",", " ").split()
        if not parts:
            continue
        if len(parts) != 2:
            raise ValueError(f"Could not read line: {line!r}")
        try:
            weight = float(parts[1])
        except ValueError as exc:
            raise ValueError(f"Weight is not a number on line: {line!r}") from exc
        if not math.isfinite(weight):
            raise ValueError(f"Weight must be a finite number: {line!r}")
        if weight < 0:
            raise ValueError(f"Weights cannot be negative: {line!r}")
        symbol = parts[0].upper()
        if symbol in out:
            raise ValueError(f"Duplicate symbol: {symbol}")
        out[symbol] = weight
    if not out:
        raise ValueError("Enter at least one holding.")
    return out


def _asset(token: str, default_exchange: str) -> str:
    """Resolve a typed asset to the same readable label ``resolve_holdings`` produces."""
    return company_label(resolve_symbol(token, default_exchange).ticker)


def parse_views(raw: str, default_exchange: str = "NSE") -> list[View]:
    """Parse Black-Litterman view lines.

    ``TCS 0.15 0.6``       absolute view: TCS returns 15% a year, 60% confident.
    ``TCS>INFY 0.03 0.5``  relative view: TCS beats INFY by 3% a year, 50% confident.
    Assets accept any form the symbol resolver does (``500325``, ``BSE:TCS``, ``INFY.NS``).
    Returns and confidences are fractions (0.15, not 15). Blank lines are skipped.
    """
    views: list[View] = []
    for line in raw.splitlines():
        parts = line.replace(",", " ").split()
        if not parts:
            continue
        if len(parts) != 3:
            raise ValueError(f"A view needs 'ASSET return confidence': {line!r}")
        target, ret_text, conf_text = parts
        try:
            expected, confidence = float(ret_text), float(conf_text)
        except ValueError as exc:
            raise ValueError(f"Return and confidence must be numbers: {line!r}") from exc
        if not math.isfinite(expected):
            raise ValueError(f"Return must be a finite number: {line!r}")
        if not 0 < confidence < 1:
            raise ValueError(f"Confidence must be strictly between 0 and 1: {line!r}")
        if ">" in target:
            winner, _, loser = target.partition(">")
            if not winner or not loser:
                raise ValueError(f"A relative view needs two different assets: {line!r}")
            winner, loser = _asset(winner, default_exchange), _asset(loser, default_exchange)
            if winner == loser:
                raise ValueError(f"A relative view needs two different assets: {line!r}")
            weights = {winner: 1.0, loser: -1.0}
        else:
            weights = {_asset(target, default_exchange): 1.0}
        views.append(View(weights=weights, expected_return=expected, confidence=confidence))
    return views


def resolve_holdings(
    holdings: dict[str, float], default_exchange: str = "NSE"
) -> tuple[dict[str, str], dict[str, float]]:
    """Map typed holdings to Yahoo tickers; returns ``(ticker_by_name, weight_by_name)``.

    Names are readable labels (``RELIANCE``, ``TCS (BSE 532540)``) so the same company listed
    on both exchanges stays distinct. Two entries that resolve to one ticker are an error
    rather than a silent merge.
    """
    tickers: dict[str, str] = {}
    weights: dict[str, float] = {}
    seen: dict[str, str] = {}
    for raw, weight in holdings.items():
        item = resolve_symbol(raw, default_exchange)
        if item.ticker in seen:
            raise ValueError(
                f"{raw} and {seen[item.ticker]} are the same security ({item.ticker})."
            )
        seen[item.ticker] = raw
        name = company_label(item.ticker)
        tickers[name] = item.ticker
        weights[name] = weight
    return tickers, weights


def parse_share_counts(
    raw: str, default_exchange: str, allowed: set[str] | frozenset[str]
) -> dict[str, int]:
    """Parse current share counts (``SYMBOL shares`` per line; blank means nothing held).

    Symbols are resolved like holdings (so ``500325`` and ``BSE:500325`` work) and must be
    one of ``allowed`` (the loaded portfolio's names). Counts must be whole, non-negative.
    """
    if not raw.strip():
        return {}
    names, counts = resolve_holdings(parse_holdings(raw), default_exchange)
    unknown = [name for name in names if name not in allowed]
    if unknown:
        raise ValueError(f"Not in the loaded portfolio: {', '.join(unknown)}")
    out: dict[str, int] = {}
    for name, count in counts.items():
        if not float(count).is_integer():
            raise ValueError(f"Share counts must be whole numbers: {name} {count}")
        out[name] = int(count)
    return out
