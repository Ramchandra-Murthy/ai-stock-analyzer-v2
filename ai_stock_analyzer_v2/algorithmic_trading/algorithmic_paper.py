"""Paper-trading adapter for algorithmic scanner decisions."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from algorithmic_trading.paper_trading import PaperFill, PaperPortfolio
from algorithmic_trading.trading_journal import (
    TradeExecution,
    TradeOrder,
    reconcile_orders,
)


@dataclass(frozen=True)
class PaperRebalance:
    """Result of applying scanner target positions to a paper portfolio."""

    orders: tuple[TradeOrder, ...]
    fills: tuple[PaperFill, ...]
    reconciliation: tuple
    equity: float


def rebalance_from_scan(
    portfolio: PaperPortfolio,
    scan: pd.DataFrame,
) -> PaperRebalance:
    """Move a paper portfolio toward scanner LONG/SHORT/FLAT targets."""
    required = {"symbol", "price", "signal", "quantity"}
    missing = required.difference(scan.columns)
    if missing:
        raise ValueError(f"scan is missing required columns: {sorted(missing)}")

    orders: list[TradeOrder] = []
    fills: list[PaperFill] = []

    for row_number, row in scan.iterrows():
        symbol = str(row["symbol"]).strip()
        price = float(row["price"])
        quantity = int(row["quantity"])
        signal = str(row["signal"]).upper()

        if signal not in {"LONG", "SHORT", "FLAT"}:
            raise ValueError(f"unsupported signal: {signal}")

        target = quantity if signal == "LONG" else -quantity if signal == "SHORT" else 0
        current = portfolio.positions.get(symbol, 0)
        delta = target - current
        if delta == 0:
            continue

        order = TradeOrder(
            order_id=f"paper-{row_number}-{symbol}",
            symbol=symbol,
            quantity=delta,
            price=price,
        )
        fill = portfolio.submit_market_order(
            symbol=symbol,
            quantity=delta,
            price=price,
        )
        orders.append(order)
        fills.append(fill)

    executions = [
        TradeExecution(
            execution_id=f"fill-{index}",
            symbol=fill.symbol,
            quantity=fill.quantity if fill.side == "BUY" else -fill.quantity,
            price=fill.price,
        )
        for index, fill in enumerate(fills)
    ]
    reconciliation = tuple(reconcile_orders(orders, executions))
    prices = {str(row["symbol"]): float(row["price"]) for _, row in scan.iterrows()}
    equity = portfolio.mark_to_market(prices)

    return PaperRebalance(
        orders=tuple(orders),
        fills=tuple(fills),
        reconciliation=reconciliation,
        equity=equity,
    )
