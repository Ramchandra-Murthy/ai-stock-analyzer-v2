"""Deterministic, long-only OHLC backtesting utilities for research.

Signals are evaluated at a bar close and can only enter at the next bar's open.
This module is a research harness, not a trade recommendation or execution system.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from math import isfinite


@dataclass(frozen=True)
class Candle:
    """One chronologically ordered OHLC bar."""

    timestamp: str
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class BacktestConfig:
    """Backtest assumptions; all costs are expressed in price units per share."""

    capital: float = 10_000.0
    max_loss_per_trade: float = 500.0
    stop_distance: float = 5.0
    reward_risk_ratio: float = 2.0
    round_trip_cost_per_unit: float = 0.0
    slippage_per_unit_per_side: float = 0.0


@dataclass(frozen=True)
class Trade:
    entry_timestamp: str
    exit_timestamp: str
    entry_price: float
    exit_price: float
    quantity: int
    gross_pnl: float
    costs: float
    net_pnl: float
    exit_reason: str


@dataclass(frozen=True)
class BacktestResult:
    trades: tuple[Trade, ...]
    starting_capital: float
    ending_capital: float
    total_return_pct: float
    win_rate_pct: float
    expectancy_per_trade: float
    profit_factor: float
    max_drawdown_pct: float
    max_intratrade_drawdown_pct: float


def _finite_positive(value: float, name: str) -> None:
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and greater than zero")


def validate_candles(candles: Sequence[Candle]) -> None:
    """Reject malformed, unordered, or duplicate-timestamp OHLC input."""
    if len(candles) < 2:
        raise ValueError("at least two candles are required")
    previous_timestamp: datetime | None = None
    previous_timezone_aware: bool | None = None
    for candle in candles:
        if not isinstance(candle.timestamp, str) or not candle.timestamp.strip():
            raise ValueError("candle timestamps must be non-empty strings")
        try:
            timestamp_text = candle.timestamp.strip()
            # fromisoformat parses actual calendar/time values; normalize the
            # common UTC suffix so ISO timestamps ending in Z are supported.
            parsed_timestamp = datetime.fromisoformat(
                timestamp_text[:-1] + "+00:00" if timestamp_text.endswith("Z") else timestamp_text
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("candle timestamps must be valid ISO 8601 date/time strings") from exc

        timezone_aware = parsed_timestamp.utcoffset() is not None
        if previous_timezone_aware is not None and timezone_aware != previous_timezone_aware:
            raise ValueError("candle timestamps must use a consistent timezone convention")
        if previous_timestamp is not None:
            try:
                if parsed_timestamp <= previous_timestamp:
                    raise ValueError("candle timestamps must be strictly increasing")
            except TypeError as exc:
                raise ValueError(
                    "candle timestamps must use a consistent timezone convention"
                ) from exc
        values = (candle.open, candle.high, candle.low, candle.close)
        if not all(isfinite(value) and value > 0 for value in values):
            raise ValueError("OHLC values must be finite and greater than zero")
        if candle.low > min(candle.open, candle.close) or candle.high < max(
            candle.open, candle.close
        ):
            raise ValueError("candle high/low do not contain open and close")
        if candle.low > candle.high:
            raise ValueError("candle low cannot exceed high")
        previous_timestamp = parsed_timestamp
        previous_timezone_aware = timezone_aware


def run_backtest(
    candles: Sequence[Candle],
    signals: Sequence[bool],
    config: BacktestConfig | None = None,
) -> BacktestResult:
    """Run a conservative one-position-at-a-time long-only OHLC simulation.

    Signals are known only after their bar closes; entry is at the next bar open.
    If stop and target are both touched in one bar, stop is assumed first. Gaps
    through stops fill at the bar open and can exceed the planned loss budget.
    Slippage is charged adversely on both sides; caller supplies round-trip
    fees/taxes per unit. Position notional is capped by current realized equity.
    max_drawdown_pct uses closed-trade equity. max_intratrade_drawdown_pct also
    marks open positions to bar highs/lows, conservatively treating each bar's high
    as occurring before its low because OHLC data cannot reveal intrabar ordering.
    """
    if config is None:
        config = BacktestConfig()
    validate_candles(candles)
    if len(signals) != len(candles):
        raise ValueError("signals length must equal candles length")
    for name, value in (
        ("capital", config.capital),
        ("max_loss_per_trade", config.max_loss_per_trade),
        ("stop_distance", config.stop_distance),
        ("reward_risk_ratio", config.reward_risk_ratio),
    ):
        _finite_positive(value, name)
    for name, value in (
        ("round_trip_cost_per_unit", config.round_trip_cost_per_unit),
        ("slippage_per_unit_per_side", config.slippage_per_unit_per_side),
    ):
        if not isfinite(value) or value < 0:
            raise ValueError(f"{name} must be finite and non-negative")
    if any(not isinstance(signal, bool) for signal in signals):
        raise ValueError("signals must contain only booleans")

    trades: list[Trade] = []
    equity = config.capital
    peak_equity = equity
    max_drawdown = 0.0
    mark_to_market_peak_equity = equity
    max_intratrade_drawdown = 0.0
    index = 0
    while index < len(candles) - 1:
        if not signals[index]:
            index += 1
            continue

        entry_bar_index = index + 1
        raw_entry = candles[entry_bar_index].open
        entry_price = raw_entry + config.slippage_per_unit_per_side
        stop_price = entry_price - config.stop_distance
        if stop_price <= 0:
            index += 1
            continue
        target_price = entry_price + config.stop_distance * config.reward_risk_ratio
        per_unit_risk = (
            config.stop_distance
            + 2 * config.slippage_per_unit_per_side
            + config.round_trip_cost_per_unit
        )
        # Never size a new position from the initial deposit after losses.
        # This caps notional exposure to current realized equity, but cannot
        # guarantee the stop-loss budget during a gap or extreme slippage.
        quantity_by_risk = int(config.max_loss_per_trade // per_unit_risk)
        quantity_by_capital = int(max(0.0, equity) // entry_price)
        quantity = min(quantity_by_risk, quantity_by_capital)
        if quantity < 1:
            # The entry bar's close signal remains valid even when this entry
            # cannot be sized; evaluate it for a possible next-bar entry.
            index = entry_bar_index
            continue

        exit_index = entry_bar_index
        raw_exit = candles[exit_index].open
        reason = "end_of_data"
        for j in range(entry_bar_index, len(candles)):
            bar = candles[j]
            exit_index = j
            liquidation_cost_per_unit = (
                config.slippage_per_unit_per_side + config.round_trip_cost_per_unit
            )
            # A gap exit occurs at the open; later highs/lows in that candle
            # happen after the modeled position is already closed.
            if bar.open <= stop_price or bar.open >= target_price:
                # Use the same non-negative exit fill as the trade ledger.
                # Extreme slippage must not create a negative mark-to-market fill.
                gap_exit_price = max(0.0, bar.open - config.slippage_per_unit_per_side)
                open_equity = (
                    equity
                    + (gap_exit_price - entry_price) * quantity
                    - config.round_trip_cost_per_unit * quantity
                )
                mark_to_market_peak_equity = max(mark_to_market_peak_equity, open_equity)
                if mark_to_market_peak_equity > 0:
                    max_intratrade_drawdown = max(
                        max_intratrade_drawdown,
                        (mark_to_market_peak_equity - open_equity) / mark_to_market_peak_equity,
                    )
                if bar.open <= stop_price:
                    raw_exit, reason = bar.open, "stop_gap"
                else:
                    raw_exit, reason = bar.open, "target_gap"
                break

            # For an intrabar exit, high-before-low is deliberately conservative
            # because OHLC data cannot reveal the order of the extremes.
            high_equity = equity + (bar.high - entry_price - liquidation_cost_per_unit) * quantity
            low_equity = equity + (bar.low - entry_price - liquidation_cost_per_unit) * quantity
            mark_to_market_peak_equity = max(mark_to_market_peak_equity, high_equity)
            if mark_to_market_peak_equity > 0:
                max_intratrade_drawdown = max(
                    max_intratrade_drawdown,
                    (mark_to_market_peak_equity - low_equity) / mark_to_market_peak_equity,
                )
            if bar.low <= stop_price:
                raw_exit, reason = stop_price, "stop"
                break
            if bar.high >= target_price:
                raw_exit, reason = target_price, "target"
                break
            if j == len(candles) - 1:
                raw_exit, reason = bar.close, "end_of_data"

        # An execution price cannot fall below zero. Extreme slippage assumptions
        # must not create an impossible negative exit fill in this long-only model.
        exit_price = max(0.0, raw_exit - config.slippage_per_unit_per_side)
        gross_pnl = (exit_price - entry_price) * quantity
        costs = config.round_trip_cost_per_unit * quantity
        net_pnl = gross_pnl - costs
        trades.append(
            Trade(
                entry_timestamp=candles[entry_bar_index].timestamp,
                exit_timestamp=candles[exit_index].timestamp,
                entry_price=entry_price,
                exit_price=exit_price,
                quantity=quantity,
                gross_pnl=gross_pnl,
                costs=costs,
                net_pnl=net_pnl,
                exit_reason=reason,
            )
        )
        equity += net_pnl
        mark_to_market_peak_equity = max(mark_to_market_peak_equity, equity)
        peak_equity = max(peak_equity, equity)
        if peak_equity > 0:
            max_drawdown = max(max_drawdown, (peak_equity - equity) / peak_equity)
        # The exit bar's close signal is known after the intrabar exit and may
        # enter a fresh position at the following bar's open.
        index = exit_index

    pnls = [trade.net_pnl for trade in trades]
    winners = [pnl for pnl in pnls if pnl > 0]
    losers = [pnl for pnl in pnls if pnl < 0]
    gross_wins = sum(winners)
    gross_losses = abs(sum(losers))
    return BacktestResult(
        trades=tuple(trades),
        starting_capital=config.capital,
        ending_capital=equity,
        total_return_pct=(equity / config.capital - 1) * 100,
        win_rate_pct=(len(winners) / len(trades) * 100) if trades else 0.0,
        expectancy_per_trade=(sum(pnls) / len(pnls)) if pnls else 0.0,
        profit_factor=(
            (gross_wins / gross_losses) if gross_losses else (float("inf") if gross_wins else 0.0)
        ),
        max_drawdown_pct=max_drawdown * 100,
        max_intratrade_drawdown_pct=max_intratrade_drawdown * 100,
    )
