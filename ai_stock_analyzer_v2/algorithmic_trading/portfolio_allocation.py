"""Portfolio-level risk limits and allocation for NSE/BSE research."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from algorithmic_trading.asset_allocation import (
    apply_weight_cap,
    equal_weight,
    inverse_volatility_weight,
)
from algorithmic_trading.portfolio_risk import (
    gross_exposure,
    net_beta_exposure,
    net_exposure,
)


@dataclass(frozen=True)
class PortfolioLimits:
    """Explicit portfolio limits used by the allocation layer."""

    max_gross_exposure: float = 1.0
    max_net_exposure: float = 1.0
    max_position_weight: float = 0.20
    max_positions: int = 10
    risk_fraction: float = 0.01


@dataclass(frozen=True)
class PortfolioSnapshot:
    """Auditable portfolio exposure and allocation summary."""

    weights: pd.Series
    gross: float
    net: float
    net_beta: float
    positions: int
    allowed: bool


def allocate_scan(
    scan: pd.DataFrame,
    returns: pd.DataFrame,
    limits: PortfolioLimits,
    method: str = "equal",
) -> pd.DataFrame:
    """Allocate selected scanner signals subject to portfolio limits."""
    required = {"symbol", "signal", "signal_score"}
    missing = required.difference(scan.columns)
    if missing:
        raise ValueError(f"scan is missing required columns: {sorted(missing)}")
    if limits.max_gross_exposure <= 0:
        raise ValueError("max_gross_exposure must be greater than zero")
    if limits.max_net_exposure <= 0:
        raise ValueError("max_net_exposure must be greater than zero")
    if limits.max_positions <= 0:
        raise ValueError("max_positions must be greater than zero")
    if method not in {"equal", "inverse_volatility"}:
        raise ValueError("unsupported allocation method")

    candidates = scan.loc[scan["signal"].isin(["LONG", "SHORT"])].copy()
    candidates = candidates.sort_values("signal_score", ascending=False).head(limits.max_positions)
    if candidates.empty:
        return candidates.assign(target_weight=pd.Series(dtype=float))

    symbols = candidates["symbol"].astype(str).tolist()
    available = returns.reindex(columns=symbols)
    weights = equal_weight(available) if method == "equal" else inverse_volatility_weight(available)
    weights = apply_weight_cap(weights, limits.max_position_weight)

    directions = candidates.set_index("symbol")["signal"].map({"LONG": 1.0, "SHORT": -1.0})
    signed = weights.reindex(symbols).fillna(0.0) * directions.reindex(symbols)
    gross = float(signed.abs().sum())
    if gross > limits.max_gross_exposure and gross > 0:
        signed *= limits.max_gross_exposure / gross

    net = float(signed.sum())
    if abs(net) > limits.max_net_exposure and abs(net) > 0:
        signed *= limits.max_net_exposure / abs(net)

    result = candidates[["symbol", "signal", "signal_score"]].copy()
    result["target_weight"] = result["symbol"].map(signed)
    return result.reset_index(drop=True)


def snapshot(
    market_values: pd.DataFrame,
    nav: pd.Series,
    beta: pd.Series,
    limits: PortfolioLimits,
) -> PortfolioSnapshot:
    """Evaluate current gross, net and beta-weighted portfolio exposure."""
    gross_series = gross_exposure(market_values, nav).dropna()
    net_series = net_exposure(market_values, nav).dropna()
    beta_series = net_beta_exposure(market_values, beta, nav).dropna()

    gross = float(gross_series.iloc[-1]) if not gross_series.empty else 0.0
    net = float(net_series.iloc[-1]) if not net_series.empty else 0.0
    net_beta = float(beta_series.iloc[-1]) if not beta_series.empty else 0.0

    weights = (
        market_values.iloc[-1].div(nav.iloc[-1])
        if not market_values.empty and nav.iloc[-1] != 0
        else pd.Series(dtype=float)
    )
    positions = int((weights.abs() > 0).sum())
    allowed = (
        gross <= limits.max_gross_exposure + 1e-12
        and abs(net) <= limits.max_net_exposure + 1e-12
        and positions <= limits.max_positions
    )

    return PortfolioSnapshot(
        weights=weights,
        gross=gross,
        net=net,
        net_beta=net_beta,
        positions=positions,
        allowed=allowed,
    )
