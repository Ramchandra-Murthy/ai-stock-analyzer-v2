"""Approximate sector for each stock in the curated NSE/BSE universe (``scanner.universe``).

A coarse, hand-assigned grouping of 17 sectors for concentration reporting, not an official
index classification. Diversified groups sit in their largest business (for example RELIANCE in
oil, gas & energy). Edit :data:`SECTOR_BY_NSE_NAME` if you disagree; a test keeps it in step
with the universe list. Stocks outside the list simply report as unmapped.
"""

from __future__ import annotations

from services.symbol_resolver import resolve_symbol

UNMAPPED = "Unmapped"

_GROUPS: dict[str, list[str]] = {
    "Banks": (
        "HDFCBANK ICICIBANK SBIN KOTAKBANK AXISBANK INDUSINDBK BANKBARODA CANBK IDFCFIRSTB PNB"
    ).split(),
    "Financial services": "BAJFINANCE BAJAJFINSV JIOFIN IRFC".split(),
    "Insurance": "ICICIGI SBILIFE HDFCLIFE LICI".split(),
    "IT services": "TCS INFY HCLTECH WIPRO TECHM".split(),
    "Oil, gas & energy": "RELIANCE ONGC BPCL IOC GAIL".split(),
    "Power & utilities": "NTPC POWERGRID".split(),
    "Metals & mining": "COALINDIA TATASTEEL JSWSTEEL HINDALCO VEDL".split(),
    "Automobiles": (
        "MARUTI M&M TATAMOTORS EICHERMOT HEROMOTOCO BAJAJ-AUTO TVSMOTOR ASHOKLEY MOTHERSON"
    ).split(),
    "FMCG": "ITC HINDUNILVR NESTLEIND BRITANNIA TATACONSUM DABUR GODREJCP COLPAL".split(),
    "Consumer & retail": "TITAN TRENT DMART".split(),
    "Internet & new-age": "ZOMATO NYKAA PAYTM".split(),
    "Healthcare": "SUNPHARMA CIPLA DRREDDY DIVISLAB APOLLOHOSP".split(),
    "Capital goods & defence": "LT BEL HAL SIEMENS ABB HAVELLS".split(),
    "Construction, cement & infra": "ULTRACEMCO GRASIM RVNL".split(),
    "Transport & logistics": "ADANIPORTS INDIGO".split(),
    "Real estate": "DLF LODHA".split(),
    "Chemicals & paints": "ASIANPAINT PIDILITIND".split(),
    "Telecom": ["BHARTIARTL"],
    "Diversified": ["ADANIENT"],
}

SECTOR_BY_NSE_NAME: dict[str, str] = {
    name: sector for sector, names in _GROUPS.items() for name in names
}


def _bse_code_to_nse_name() -> dict[str, str]:
    from scanner.universe import BSE_CANDIDATES, NSE_CANDIDATES

    return dict(zip(BSE_CANDIDATES, NSE_CANDIDATES, strict=True))


def sector_for_ticker(ticker: str) -> str:
    """Sector for ``TCS.NS``, ``500325.BO``, ``NSE:TCS`` and so on; ``UNMAPPED`` if unknown."""
    try:
        item = resolve_symbol(ticker)
    except ValueError:
        return UNMAPPED
    name = item.code
    if item.is_bse_scrip_code:
        name = _bse_code_to_nse_name().get(item.code, item.code)
    return SECTOR_BY_NSE_NAME.get(name, UNMAPPED)
