"""Walk-forward backtesting for the leakage-safe AI trading model."""

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from ai_trading.ml_model import predict_latest, train_model


@dataclass(frozen=True)
class BacktestResult:
    """Summary statistics for a non-overlapping walk-forward test."""

    total_return: float
    max_drawdown: float
    trades: int
    win_rate: float
    profit_factor: float | None
    final_equity: float


def walk_forward_backtest(
    frame: pd.DataFrame,
    *,
    horizon: int = 5,
    threshold: float = 0.01,
    long_probability: float = 0.55,
    short_probability: float = 0.45,
    initial_train: int = 100,
    transaction_cost_bps: float = 10.0,
) -> tuple[pd.DataFrame, BacktestResult]:
    """Run an expanding-window, non-overlapping ML backtest.

    Each model is trained only on observations whose future labels are already
    known before the prediction date. Predictions use data available through
    the decision bar's close, then enter on the next bar (at its open when
    available). Each trade holds for the configured horizon without overlap.
    The chronological validation holdout is scored first, then the model is
    refit on all labelled observations that were available before the decision
    timestamp.
    """
    if horizon < 1:
        raise ValueError("horizon must be at least 1")
    if not 0.5 <= long_probability <= 1.0:
        raise ValueError("long_probability must be between 0.5 and 1.0")
    if not 0.0 <= short_probability <= 0.5:
        raise ValueError("short_probability must be between 0.0 and 0.5")
    if short_probability >= long_probability:
        raise ValueError("short_probability must be below long_probability")
    if initial_train < 30:
        raise ValueError("initial_train must be at least 30")
    if not math.isfinite(transaction_cost_bps) or transaction_cost_bps < 0:
        raise ValueError("transaction_cost_bps must be finite and non-negative")

    close = pd.to_numeric(frame["Close"], errors="coerce")
    has_open = "Open" in frame.columns
    open_prices = pd.to_numeric(frame["Open"], errors="coerce") if has_open else close
    # With OHLC data, enter at the next bar's open and exit at the close
    # horizon bars after the decision bar. For close-only data, delay entry
    # until the next close and extend the exit by one bar to preserve holding
    # duration without pretending the decision-bar close was executable.
    exit_offset = horizon if has_open else horizon + 1
    rows: list[dict[str, object]] = []

    for prediction_index in range(initial_train, len(frame) - exit_offset, horizon):
        train_frame = frame.iloc[:prediction_index].copy()
        prediction_frame = frame.iloc[: prediction_index + 1].copy()
        try:
            model, _ = train_model(
                train_frame,
                horizon=horizon,
                threshold=threshold,
                test_fraction=0.2,
                refit_full=True,
            )
            prediction = predict_latest(model, prediction_frame)
        except (TypeError, ValueError, KeyError):
            continue

        probability = float(prediction["probability_up"])
        if probability >= long_probability:
            signal = "LONG"
            direction = 1.0
        elif probability <= short_probability:
            signal = "SHORT"
            direction = -1.0
        else:
            signal = "FLAT"
            direction = 0.0

        entry_index = prediction_index + 1
        exit_index = prediction_index + exit_offset
        entry = float(open_prices.iloc[entry_index] if has_open else close.iloc[entry_index])
        exit_price = float(close.iloc[exit_index])
        if not all(math.isfinite(price) and price > 0.0 for price in (entry, exit_price)):
            continue

        gross_return = direction * (exit_price / entry - 1.0) if direction else 0.0
        cost = (2.0 * transaction_cost_bps) / 10000.0 if direction else 0.0
        net_return = gross_return - cost

        rows.append(
            {
                "decision_index": frame.index[prediction_index],
                "entry_index": frame.index[entry_index],
                "exit_index": frame.index[exit_index],
                "signal": signal,
                "probability_up": probability,
                "entry_price": entry,
                "exit_price": exit_price,
                "gross_return": gross_return,
                "transaction_cost": cost,
                "net_return": net_return,
            }
        )

    trades = pd.DataFrame(rows)
    if trades.empty:
        raise ValueError("no valid walk-forward trades were produced")

    trades["equity"] = (1.0 + trades["net_return"]).cumprod()
    running_peak = trades["equity"].cummax()
    trades["drawdown"] = trades["equity"] / running_peak - 1.0

    active = trades[trades["signal"] != "FLAT"]
    winners = active[active["net_return"] > 0.0]
    gross_profit = float(active.loc[active["net_return"] > 0.0, "net_return"].sum())
    gross_loss = float(-active.loc[active["net_return"] < 0.0, "net_return"].sum())

    result = BacktestResult(
        total_return=float(trades["equity"].iloc[-1] - 1.0),
        max_drawdown=float(trades["drawdown"].min()),
        trades=len(active),
        win_rate=float(len(winners) / len(active)) if not active.empty else 0.0,
        profit_factor=(gross_profit / gross_loss if gross_loss > 0.0 else None),
        final_equity=float(trades["equity"].iloc[-1]),
    )
    return trades, result
