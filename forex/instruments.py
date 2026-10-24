"""Currency-pair helpers: pip size, pip value, position sizing and spread cost.

Conventions: a pair "EURUSD" is quoted as quote-currency per 1 base-currency. One standard
lot is 100,000 units of the base currency (NSE currency futures use their own contract
sizes; pass ``contract_size``). All results are estimates for planning, not broker quotes.
"""

from __future__ import annotations

from dataclasses import dataclass

MAJORS = ("EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD")
CROSSES = ("EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "EURCHF")
INR_PAIRS = ("USDINR", "EURINR", "GBPINR", "JPYINR")
ALL_PAIRS = MAJORS + CROSSES + INR_PAIRS
STANDARD_LOT = 100_000
# NSE currency derivatives quote INR pairs with a 0.0025 tick (verify contract specs with NSE).
INR_TICK = 0.0025


def normalise_pair(pair: str) -> str:
    text = pair.replace("/", "").replace("=X", "").replace("-", "").strip().upper()
    if len(text) != 6 or not text.isalpha():
        raise ValueError(f"Not a currency pair: {pair!r}")
    if text[:3] == text[3:]:
        raise ValueError("Base and quote currencies must differ.")
    return text


def split_pair(pair: str) -> tuple[str, str]:
    p = normalise_pair(pair)
    return p[:3], p[3:]


def yahoo_symbol(pair: str) -> str:
    return normalise_pair(pair) + "=X"


def pip_size(pair: str) -> float:
    """0.01 for JPY-quoted pairs, 0.0001 otherwise (INR pairs trade in 0.0025 ticks)."""
    _, quote = split_pair(pair)
    return 0.01 if quote == "JPY" else 0.0001


def price_to_pips(pair: str, price_move: float) -> float:
    return price_move / pip_size(pair)


def pips_to_price(pair: str, pips: float) -> float:
    return pips * pip_size(pair)


@dataclass(frozen=True)
class PositionSize:
    units: float
    lots: float
    risk_amount: float  # in account currency
    pip_value_account: float  # account-currency value of one pip for the whole position
    notional_account: float


def pip_value_quote(pair: str, units: float) -> float:
    """Value of one pip in the QUOTE currency for ``units`` of base."""
    return units * pip_size(pair)


def position_size(
    pair: str,
    *,
    account_balance: float,
    risk_pct: float,
    stop_pips: float,
    quote_to_account: float,
    base_to_account: float | None = None,
    contract_size: float = STANDARD_LOT,
) -> PositionSize:
    """Units so that hitting the stop loses ``risk_pct`` of the balance.

    ``quote_to_account``: units of account currency per 1 unit of the QUOTE currency (e.g. for
    EURUSD with an INR account this is USDINR). ``base_to_account`` is only used for the
    notional figure. Lots are fractional; round down to your broker's step before trading.
    """
    if account_balance <= 0 or not 0 < risk_pct <= 0.1 or stop_pips <= 0 or quote_to_account <= 0:
        raise ValueError("balance, stop_pips, rate must be positive and risk_pct in (0, 0.1]")
    risk_amount = account_balance * risk_pct
    loss_per_unit = stop_pips * pip_size(pair) * quote_to_account
    units = risk_amount / loss_per_unit
    base_rate = base_to_account if base_to_account is not None else float("nan")
    return PositionSize(
        units=units,
        lots=units / contract_size,
        risk_amount=risk_amount,
        pip_value_account=units * pip_size(pair) * quote_to_account,
        notional_account=units * base_rate if base_to_account is not None else float("nan"),
    )


def spread_cost_fraction(pair: str, price: float, spread_pips: float) -> float:
    """Round-trip spread cost as a fraction of notional (a full spread per round trip)."""
    if price <= 0 or spread_pips < 0:
        raise ValueError("price must be positive and spread_pips non-negative")
    return spread_pips * pip_size(pair) / price


def margin_required(notional_account: float, leverage: float) -> float:
    if notional_account < 0 or leverage < 1:
        raise ValueError("notional must be non-negative and leverage at least 1")
    return notional_account / leverage
