"""Market-data adapter for NIFTY Options V2 paper trading."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from engine.nifty_options_v2_live import LivePaperObservation
from strategy.nifty_options_v2 import NiftyCallContract


@dataclass(frozen=True)
class NiftyV2MarketObservation:
    """Current spot and selected CALL observation."""

    contract: NiftyCallContract
    observation: LivePaperObservation


def select_deepest_itm_call(
    chain: pd.DataFrame,
    *,
    spot: float,
    expiry: date,
    observed_date: date,
) -> NiftyV2MarketObservation:
    """Select the lowest available ITM CALL from a normalized option chain."""
    if spot <= 0:
        raise ValueError("spot must be positive")
    if observed_date >= expiry:
        raise ValueError("observation must precede expiry")

    required = {"strike", "CE LTP"}
    missing = required.difference(chain.columns)
    if missing:
        raise ValueError(f"option chain is missing required columns: {', '.join(sorted(missing))}")

    candidates = chain.loc[
        (pd.to_numeric(chain["strike"], errors="coerce") > 0)
        & (pd.to_numeric(chain["strike"], errors="coerce") < spot)
        & (pd.to_numeric(chain["CE LTP"], errors="coerce") >= 0)
    ].copy()
    candidates["strike"] = pd.to_numeric(candidates["strike"], errors="coerce")
    candidates["CE LTP"] = pd.to_numeric(candidates["CE LTP"], errors="coerce")
    candidates = candidates.dropna(subset=["strike", "CE LTP"])
    if candidates.empty:
        raise ValueError("no valid ITM CALL quote is available")

    row = candidates.sort_values("strike", ascending=True).iloc[0]
    contract = NiftyCallContract(expiry=expiry, strike=float(row["strike"]))
    observation = LivePaperObservation(
        observed_date=observed_date,
        spot=float(spot),
        ltp=float(row["CE LTP"]),
    )
    return NiftyV2MarketObservation(contract=contract, observation=observation)
