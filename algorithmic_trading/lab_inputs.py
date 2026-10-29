"""Text-input parsing for the Advanced Portfolio Lab page (pure functions, no Streamlit).

Kept separate from the page so the parsing rules can be unit tested.
"""

from __future__ import annotations

from algorithmic_trading.portfolio_advanced import View


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
        if weight < 0:
            raise ValueError(f"Weights cannot be negative: {line!r}")
        symbol = parts[0].upper()
        if symbol in out:
            raise ValueError(f"Duplicate symbol: {symbol}")
        out[symbol] = weight
    if not out:
        raise ValueError("Enter at least one holding.")
    return out


def parse_views(raw: str) -> list[View]:
    """Parse Black-Litterman view lines.

    ``TCS 0.15 0.6``       absolute view: TCS returns 15% a year, 60% confident.
    ``TCS>INFY 0.03 0.5``  relative view: TCS beats INFY by 3% a year, 50% confident.
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
        if not 0 < confidence < 1:
            raise ValueError(f"Confidence must be strictly between 0 and 1: {line!r}")
        if ">" in target:
            winner, _, loser = target.partition(">")
            winner, loser = winner.upper(), loser.upper()
            if not winner or not loser or winner == loser:
                raise ValueError(f"A relative view needs two different assets: {line!r}")
            weights = {winner: 1.0, loser: -1.0}
        else:
            weights = {target.upper(): 1.0}
        views.append(View(weights=weights, expected_return=expected, confidence=confidence))
    return views
