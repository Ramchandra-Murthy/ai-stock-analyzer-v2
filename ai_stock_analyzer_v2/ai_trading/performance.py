"""Performance analytics for the AI paper-trading portfolio."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .paper_trading import EquitySnapshot, PaperTrade


@dataclass(frozen=True)
class PerformanceReport:
    """Summary statistics for a paper-trading portfolio."""

    initial_cash: float
    current_equity: float
    total_return_pct: float
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    profit_factor: float | None
    max_drawdown_pct: float
    gross_exposure_pct: float
    trade_count: int


def build_performance_report(
    initial_cash: float,
    trades: list[PaperTrade],
    positions: dict[str, int],
    entry_prices: dict[str, float],
    prices: dict[str, float],
    current_equity: float,
) -> PerformanceReport:
    """Build performance metrics from the paper trade ledger and holdings."""
    if initial_cash <= 0:
        raise ValueError("initial_cash must be positive")
    if current_equity < 0:
        raise ValueError("current_equity cannot be negative")

    lots: dict[str, list[tuple[int, float]]] = {}
    realized_pnl = 0.0
    wins = 0
    losses = 0
    gross_profit = 0.0
    gross_loss = 0.0
    realized_equity = [float(initial_cash)]

    for trade in trades:
        symbol = trade.symbol
        if trade.side == "BUY":
            lots.setdefault(symbol, []).append((trade.quantity, trade.price))
            continue

        remaining = trade.quantity
        sell_order_pnl = 0.0
        while remaining > 0 and lots.get(symbol):
            quantity, entry = lots[symbol][0]
            matched = min(remaining, quantity)
            pnl = matched * (trade.price - entry)
            realized_pnl += pnl
            sell_order_pnl += pnl
            remaining -= matched
            if matched == quantity:
                lots[symbol].pop(0)
            else:
                lots[symbol][0] = (quantity - matched, entry)

        # Count each sell order once, using its aggregate P&L across matched lots.
        if sell_order_pnl > 0:
            wins += 1
            gross_profit += sell_order_pnl
        elif sell_order_pnl < 0:
            losses += 1
            gross_loss += -sell_order_pnl
        realized_equity.append(initial_cash + realized_pnl)

    unrealized_pnl = 0.0
    for symbol, quantity in positions.items():
        price = prices.get(symbol)
        if price is None:
            continue
        open_lots = lots.get(symbol, [])
        cost = sum(lot_quantity * entry for lot_quantity, entry in open_lots)
        if not open_lots and symbol in entry_prices:
            cost = quantity * entry_prices[symbol]
        unrealized_pnl += quantity * price - cost

    total_pnl = current_equity - initial_cash
    total_return_pct = total_pnl / initial_cash * 100.0
    win_rate_pct = wins / (wins + losses) * 100.0 if wins + losses else 0.0
    profit_factor = (
        gross_profit / gross_loss if gross_loss else (float("inf") if gross_profit else None)
    )

    peak = realized_equity[0]
    max_drawdown = 0.0
    for equity in realized_equity:
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - equity) / peak * 100.0)

    market_value = sum(
        quantity * float(prices[symbol])
        for symbol, quantity in positions.items()
        if symbol in prices
    )
    gross_exposure_pct = market_value / current_equity * 100.0 if current_equity > 0 else 0.0

    return PerformanceReport(
        initial_cash=float(initial_cash),
        current_equity=float(current_equity),
        total_return_pct=float(total_return_pct),
        realized_pnl=float(realized_pnl),
        unrealized_pnl=float(unrealized_pnl),
        total_pnl=float(total_pnl),
        winning_trades=wins,
        losing_trades=losses,
        win_rate_pct=float(win_rate_pct),
        profit_factor=profit_factor,
        max_drawdown_pct=float(max_drawdown),
        gross_exposure_pct=float(gross_exposure_pct),
        trade_count=len(trades),
    )


def build_equity_curve(
    snapshots: list[EquitySnapshot],
) -> pd.DataFrame:
    """Build return and drawdown analytics from recorded equity snapshots."""
    if not snapshots:
        return pd.DataFrame(columns=["timestamp", "equity", "return_pct", "drawdown_pct"])

    curve = pd.DataFrame(
        {
            "timestamp": [snapshot.timestamp for snapshot in snapshots],
            "equity": [snapshot.equity for snapshot in snapshots],
        }
    )
    initial = float(curve.iloc[0]["equity"])
    curve["return_pct"] = (curve["equity"] / initial - 1.0) * 100.0
    curve["peak_equity"] = curve["equity"].cummax()
    curve["drawdown_pct"] = (curve["peak_equity"] - curve["equity"]) / curve["peak_equity"] * 100.0
    return curve.drop(columns=["peak_equity"])
