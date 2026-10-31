"""One place that turns whatever a user typed into a Yahoo Finance ticker and an exchange.

The app grew several private copies of "append .NS or .BO" that disagree on edge cases.
New code should use :func:`resolve_symbol`; it accepts every form people actually type:

* ``RELIANCE``                     plain name (exchange comes from ``default_exchange``)
* ``RELIANCE.NS`` / ``500325.BO``  explicit Yahoo suffix (authoritative)
* ``NSE:TCS`` / ``BSE:500325``     exchange prefix (authoritative)
* ``500325``                       a six-digit BSE scrip code (only BSE uses these, so the
  exchange is inferred even when the default is NSE)

The module is pure (no network, no Streamlit) so it can be unit tested.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

NSE = "NSE"
BSE = "BSE"
SUFFIX = {NSE: ".NS", BSE: ".BO"}
_SUFFIX_TO_EXCHANGE = {".NS": NSE, ".NSE": NSE, ".BO": BSE, ".BSE": BSE}
_PREFIX_TO_EXCHANGE = {"NSE": NSE, "BSE": BSE, "BOM": BSE}
_CODE = re.compile(r"^[A-Z0-9&_\-]{1,20}$")
_BSE_SCRIP = re.compile(r"^\d{6}$")


@dataclass(frozen=True)
class ResolvedSymbol:
    ticker: str  # Yahoo Finance ticker, e.g. "500325.BO"
    exchange: str  # "NSE" or "BSE"
    code: str  # the symbol without any suffix, e.g. "500325"

    @property
    def is_bse_scrip_code(self) -> bool:
        return self.exchange == BSE and bool(_BSE_SCRIP.match(self.code))


def resolve_symbol(raw: str, default_exchange: str = NSE) -> ResolvedSymbol:
    """Resolve user input to a :class:`ResolvedSymbol`; raises ``ValueError`` if unusable."""
    default = str(default_exchange).strip().upper()
    if default not in SUFFIX:
        raise ValueError("exchange must be NSE or BSE")
    text = str(raw or "").strip().upper()
    if not text:
        raise ValueError("Enter a symbol.")

    prefix_exchange: str | None = None
    if ":" in text:
        prefix, _, text = text.partition(":")
        if prefix.strip() not in _PREFIX_TO_EXCHANGE:
            raise ValueError(f"Unknown exchange prefix '{prefix.strip()}'; use NSE: or BSE:.")
        prefix_exchange = _PREFIX_TO_EXCHANGE[prefix.strip()]
        text = text.strip()

    suffix_exchange: str | None = None
    for suffix, exchange in _SUFFIX_TO_EXCHANGE.items():
        if text.endswith(suffix) and len(text) > len(suffix):
            suffix_exchange, text = exchange, text[: -len(suffix)]
            break

    if prefix_exchange and suffix_exchange and prefix_exchange != suffix_exchange:
        raise ValueError("The exchange prefix and the ticker suffix disagree.")
    if not _CODE.match(text):
        raise ValueError(f"'{text}' is not a valid NSE/BSE symbol.")

    exchange = prefix_exchange or suffix_exchange
    if exchange is None:
        # Only BSE uses six-digit scrip codes, so a bare code cannot be an NSE symbol.
        exchange = BSE if _BSE_SCRIP.match(text) else default
    if exchange == NSE and _BSE_SCRIP.match(text):
        raise ValueError(f"{text} looks like a BSE scrip code, not an NSE symbol.")
    return ResolvedSymbol(ticker=f"{text}{SUFFIX[exchange]}", exchange=exchange, code=text)


def resolve_many(raw: str, default_exchange: str = NSE) -> tuple[list[ResolvedSymbol], list[str]]:
    """Resolve a comma/space/newline separated list; returns ``(resolved, problems)``.

    Duplicates are dropped (first wins). A bad entry is reported, never silently skipped.
    """
    resolved: dict[str, ResolvedSymbol] = {}
    problems: list[str] = []
    for token in re.split(r"[,\s;]+", str(raw or "")):
        if not token:
            continue
        try:
            item = resolve_symbol(token, default_exchange)
        except ValueError as exc:
            problems.append(f"{token}: {exc}")
        else:
            resolved.setdefault(item.ticker, item)
    return list(resolved.values()), problems


@lru_cache(maxsize=1)
def _bse_code_to_name() -> dict[str, str]:
    from scanner.universe import BSE_CANDIDATES, NSE_CANDIDATES

    # The curated lists are kept in matching company order (see scanner.universe).
    return dict(zip(BSE_CANDIDATES, NSE_CANDIDATES, strict=True))


def company_label(ticker: str) -> str:
    """Readable label: ``RELIANCE (BSE 500325)`` for curated scrip codes, else the symbol."""
    try:
        item = resolve_symbol(ticker)
    except ValueError:
        return str(ticker)
    if item.is_bse_scrip_code:
        name = _bse_code_to_name().get(item.code)
        if name:
            return f"{name} (BSE {item.code})"
    if item.exchange == BSE:
        # Keeps "TCS" (NSE) and "TCS" (BSE) distinguishable in tables and column headers.
        return f"{item.code} (BSE)"
    return item.code


def yahoo_ticker(ticker: str) -> str:
    """The Yahoo ticker that actually serves data for ``ticker``.

    Measured on Streamlit Cloud (Data Health): ``RELIANCE.BO`` (name) loaded 24/24 but
    ``500325.BO`` (scrip code) loaded 0/24. A curated BSE scrip code is therefore mapped to
    its ``NAME.BO`` form; everything else is returned unchanged (upper-cased).
    """
    text = str(ticker or "").strip().upper()
    try:
        item = resolve_symbol(text)
    except ValueError:
        return text
    if item.is_bse_scrip_code:
        name = _bse_code_to_name().get(item.code)
        if name:
            return f"{name}{SUFFIX[BSE]}"
    return text
