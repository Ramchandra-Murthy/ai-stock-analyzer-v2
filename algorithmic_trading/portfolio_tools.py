"""Minimum-CVaR optimisation and rebalance planning (research only; pure, no network).

``min_cvar_weights`` minimises expected shortfall directly with the Rockafellar-Uryasev linear
programme, so it targets the tail instead of variance. Like every optimiser fitted to history
it is an in-sample result: expect worse out of sample.

``rebalance_plan`` turns target weights into whole-share (or whole-lot) trades with estimated
NSE costs. It never assumes fractional shares and never spends cash it does not have.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy.sparse import bmat, csr_matrix, hstack, identity

from algorithmic_trading.trading_costs import IndiaEquityCostModel, india_cost_model

MIN_OBSERVATIONS = 60


def portfolio_cvar(returns: pd.DataFrame, weights: pd.Series, level: float = 0.95) -> float:
    """Average loss over the worst ``(1 - level)`` share of days (exact, fractional tail)."""
    if not 0.5 < level < 1:
        raise ValueError("level must be between 0.5 and 1.")
    losses = -(returns[list(weights.index)].to_numpy(dtype=float) @ weights.to_numpy(dtype=float))
    ordered = np.sort(losses)[::-1]
    tail = (1.0 - level) * len(ordered)
    whole = int(math.floor(tail + 1e-12))
    total = float(ordered[:whole].sum())
    if tail - whole > 1e-12:
        total += (tail - whole) * float(ordered[whole])
    return total / tail


def min_cvar_weights(
    returns: pd.DataFrame, level: float = 0.95, max_weight: float = 1.0
) -> tuple[pd.Series, float]:
    """Long-only, fully invested weights minimising CVaR; returns ``(weights, cvar)``.

    ``cvar`` is a positive daily loss fraction at ``level`` on the supplied history.
    """
    if not 0.5 < level < 1:
        raise ValueError("level must be between 0.5 and 1.")
    clean = returns.dropna()
    t, n = clean.shape
    if t < MIN_OBSERVATIONS or n < 2:
        raise ValueError(f"Need at least {MIN_OBSERVATIONS} rows and 2 assets with complete data.")
    if not 0 < max_weight <= 1 or max_weight * n < 1 - 1e-12:
        raise ValueError("max_weight must be in (0, 1] and large enough to be fully invested.")
    r = clean.to_numpy(dtype=float)
    # Variables: [w (n), alpha (1), u (t)].  minimise alpha + sum(u) / ((1 - level) * t)
    # subject to  -r_t . w - alpha - u_t <= 0,  u >= 0,  sum(w) = 1,  0 <= w <= max_weight.
    cost = np.concatenate([np.zeros(n), [1.0], np.full(t, 1.0 / ((1.0 - level) * t))])
    a_ub = hstack([csr_matrix(-r), csr_matrix(-np.ones((t, 1))), -identity(t, format="csr")])
    a_eq = bmat([[csr_matrix(np.ones((1, n))), csr_matrix((1, 1)), csr_matrix((1, t))]])
    bounds = [(0.0, max_weight)] * n + [(None, None)] + [(0.0, None)] * t
    result = linprog(
        cost,
        A_ub=a_ub,
        b_ub=np.zeros(t),
        A_eq=a_eq,
        b_eq=[1.0],
        bounds=bounds,
        method="highs",
    )
    if not result.success:
        raise ValueError(f"The optimiser did not converge: {result.message}")
    w = np.clip(result.x[:n], 0.0, max_weight)
    weights = pd.Series(w / w.sum(), index=clean.columns)
    return weights, portfolio_cvar(clean, weights, level)


def _round_to_lot(shares: float, lot: int) -> int:
    """Round toward zero to a whole number of lots."""
    return int(math.trunc(shares / lot)) * lot


def rebalance_plan(
    shares: dict[str, int],
    prices: dict[str, float],
    target_weights: dict[str, float] | pd.Series,
    *,
    cash: float = 0.0,
    lot_sizes: dict[str, int] | None = None,
    min_trade_value: float = 0.0,
    cost_model: IndiaEquityCostModel | None = None,
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Trades that move ``shares`` toward ``target_weights``; returns ``(plan, summary)``.

    Weights are shares of total portfolio value (holdings plus ``cash``) and may sum to less
    than 1, leaving a cash target. Trades round toward zero to whole lots, trades smaller than
    ``min_trade_value`` are skipped, and buys are trimmed one lot at a time until estimated
    costs fit inside available cash. Costs use NSE delivery rates by default, an approximation
    for BSE listings.
    """
    names = list(dict.fromkeys([*shares, *dict(pd.Series(target_weights, dtype=float))]))
    target = pd.Series(target_weights, dtype=float).reindex(names).fillna(0.0)
    if (target < 0).any() or target.sum() > 1.0 + 1e-9:
        raise ValueError("Target weights must be non-negative and sum to at most 1.")
    held = pd.Series(shares, dtype=float).reindex(names).fillna(0.0)
    if (held < 0).any() or (held % 1 != 0).any():
        raise ValueError("Current shares must be whole, non-negative numbers.")
    missing = [n for n in names if n not in prices or not prices[n] or prices[n] <= 0]
    if missing:
        raise ValueError(f"No valid price for: {', '.join(missing)}")
    if cash < 0:
        raise ValueError("cash cannot be negative.")
    price = pd.Series(prices, dtype=float).reindex(names)
    lots = pd.Series(
        {n: int((lot_sizes or {}).get(n, 1)) for n in names}, dtype=float
    ).reindex(names)
    if (lots < 1).any():
        raise ValueError("Lot sizes must be at least 1.")
    model = cost_model or india_cost_model("delivery")

    value = float((held * price).sum() + cash)
    if value <= 0:
        raise ValueError("The portfolio has no value to rebalance.")
    wanted = target * value / price - held
    trade = pd.Series(
        {n: _round_to_lot(float(wanted[n]), int(lots[n])) for n in names}, dtype=float
    )
    trade[(trade.abs() * price) < min_trade_value] = 0.0

    def totals(t: pd.Series) -> tuple[float, float, float]:
        buys = float((t.clip(lower=0) * price).sum())
        sells = float((-t.clip(upper=0) * price).sum())
        fee = float(
            model.cost_fraction(
                pd.Series([buys]), pd.Series([sells])
            ).iloc[0]
        )
        return buys, sells, fee

    # Costs are a share of traded value, so recompute after every trim.
    for _ in range(10_000):
        buys, sells, fee = totals(trade)
        if cash + sells - buys - fee >= -1e-9:
            break
        candidates = trade[trade > 0]
        if candidates.empty:
            break
        biggest = (candidates * price[candidates.index]).idxmax()
        trade[biggest] -= lots[biggest]
    buys, sells, fee = totals(trade)

    notional = trade * price
    per_asset_cost = pd.Series(
        {
            n: float(
                model.cost_fraction(
                    pd.Series([max(notional[n], 0.0)]), pd.Series([max(-notional[n], 0.0)])
                ).iloc[0]
            )
            for n in names
        }
    )
    after = held + trade
    cash_after = cash + sells - buys - fee
    plan = pd.DataFrame(
        {
            "current_shares": held.astype(int),
            "price": price,
            "current_weight": held * price / value,
            "target_weight": target,
            "trade_shares": trade.astype(int),
            "action": np.where(trade > 0, "BUY", np.where(trade < 0, "SELL", "HOLD")),
            "trade_value": notional,
            "est_cost": per_asset_cost,
            "post_trade_shares": after.astype(int),
            "post_trade_weight": after * price / value,
        }
    )
    summary = {
        "portfolio_value": value,
        "buy_value": buys,
        "sell_value": sells,
        "turnover": (buys + sells) / value,
        "estimated_cost": fee,
        "cash_after": cash_after,
        "max_weight_drift": float((plan["post_trade_weight"] - plan["target_weight"]).abs().max()),
    }
    return plan, summary
