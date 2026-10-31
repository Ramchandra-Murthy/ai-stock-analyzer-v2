"""Stop-loss, take-profit, trailing stop and a portfolio kill switch on a long-only backtest.

Research only. Everything works on daily closes: a stop is assumed to execute at the close of the
day it is breached, so gaps and intraday spikes are not modelled and real stops can fill worse.
After a guard exits a trade the strategy waits for its signal to turn off and on again before
re-entering, so a stop is not immediately undone.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


def _fraction(value: float | None, name: str) -> None:
    if value is not None and not 0 < value < 1:
        raise ValueError(f"{name} must be between 0 and 1 (for example 0.08 for 8%).")


@dataclass(frozen=True)
class GuardConfig:
    stop_loss: float | None = None
    take_profit: float | None = None
    trailing_stop: float | None = None
    kill_switch_drawdown: float | None = None  # halt all trading once equity falls this far
    cost_bps: float = 10.0  # charged per side

    def validate(self) -> None:
        _fraction(self.stop_loss, "stop_loss")
        _fraction(self.take_profit, "take_profit")
        _fraction(self.trailing_stop, "trailing_stop")
        _fraction(self.kill_switch_drawdown, "kill_switch_drawdown")
        if self.cost_bps < 0:
            raise ValueError("cost_bps cannot be negative.")


@dataclass(frozen=True)
class GuardResult:
    equity: pd.Series
    trades: pd.DataFrame
    total_return: float
    max_drawdown: float
    killed_on: pd.Timestamp | None
    exits_by_reason: dict[str, int] = field(default_factory=dict)


def _max_drawdown(equity: pd.Series) -> float:
    return float((equity / equity.cummax() - 1.0).min())


def simulate_with_guards(close: pd.Series, signal: pd.Series, config: GuardConfig) -> GuardResult:
    """Hold a long position while ``signal`` is true, subject to the guards in ``config``."""
    config.validate()
    px = pd.to_numeric(close, errors="coerce").astype(float)
    sig = signal.reindex(px.index).fillna(False).astype(bool)
    if px.isna().any() or (px <= 0).any() or len(px) < 30:
        raise ValueError("close must be at least 30 positive prices with no gaps.")
    cost = config.cost_bps / 10_000.0
    equity, peak_equity = 1.0, 1.0
    in_pos, blocked, killed_on = False, False, None
    entry = peak_px = 0.0
    entry_date = None
    entry_equity = 1.0
    curve: list[float] = []
    trades: list[dict] = []

    def close_trade(date, reason: str) -> None:
        nonlocal equity, in_pos
        equity *= 1.0 - cost
        trades.append(
            {
                "entry": entry_date,
                "exit": date,
                "return": equity / entry_equity - 1.0,
                "reason": reason,
            }
        )
        in_pos = False

    values = px.to_numpy()
    for i, date in enumerate(px.index):
        price = values[i]
        if i > 0 and in_pos:
            equity *= price / values[i - 1]
            peak_px = max(peak_px, price)
            reason = None
            if config.stop_loss is not None and price / entry - 1.0 <= -config.stop_loss:
                reason = "stop-loss"
            elif config.take_profit is not None and price / entry - 1.0 >= config.take_profit:
                reason = "take-profit"
            elif (
                config.trailing_stop is not None and price / peak_px - 1.0 <= -config.trailing_stop
            ):
                reason = "trailing stop"
            if reason:
                close_trade(date, reason)
                blocked = True
        peak_equity = max(peak_equity, equity)
        if (
            killed_on is None
            and config.kill_switch_drawdown is not None
            and equity / peak_equity - 1.0 <= -config.kill_switch_drawdown
        ):
            killed_on = date
            if in_pos:
                close_trade(date, "kill switch")
        wants = bool(sig.iloc[i])
        if not wants:
            blocked = False
            if in_pos:
                close_trade(date, "signal off")
        elif not in_pos and not blocked and killed_on is None:
            equity *= 1.0 - cost
            in_pos, entry, peak_px, entry_date, entry_equity = True, price, price, date, equity
        curve.append(equity)
    if in_pos:
        trades.append(
            {
                "entry": entry_date,
                "exit": px.index[-1],
                "return": equity / entry_equity - 1.0,
                "reason": "still open",
            }
        )
    series = pd.Series(curve, index=px.index, name="equity")
    frame = pd.DataFrame(trades, columns=["entry", "exit", "return", "reason"])
    reasons = frame["reason"].value_counts().to_dict() if not frame.empty else {}
    return GuardResult(
        equity=series,
        trades=frame,
        total_return=float(series.iloc[-1] - 1.0),
        max_drawdown=_max_drawdown(series),
        killed_on=killed_on,
        exits_by_reason={str(k): int(v) for k, v in reasons.items()},
    )


def compare_guards(
    close: pd.Series, signal: pd.Series, config: GuardConfig
) -> tuple[GuardResult, GuardResult]:
    """``(unguarded, guarded)`` on the same prices, signal and costs."""
    plain = GuardConfig(cost_bps=config.cost_bps)
    return simulate_with_guards(close, signal, plain), simulate_with_guards(close, signal, config)


def sma_crossover_signal(close: pd.Series, fast: int = 20, slow: int = 50) -> pd.Series:
    """True while the fast average is above the slow one (a plain trend rule to test guards on)."""
    if not 1 <= fast < slow:
        raise ValueError("need 1 <= fast < slow.")
    f, s = close.rolling(fast).mean(), close.rolling(slow).mean()
    return ((f > s) & s.notna()).rename("signal")
