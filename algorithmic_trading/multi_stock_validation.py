"""Cross-sectional walk-forward validation for multiple symbols."""

from __future__ import annotations

import pandas as pd

from algorithmic_trading.signal_backtest import generate_pipeline_signals
from algorithmic_trading.trading_costs import IndiaEquityCostModel
from algorithmic_trading.walk_forward_validation import walk_forward_evaluate


def _skip_category(reason: str) -> str:
    """Map a validation failure to a stable, machine-readable category."""
    message = reason.lower()
    if "benchmark" in message:
        return "benchmark_data"
    if "insufficient observations" in message:
        return "insufficient_history"
    if "missing required columns" in message or "empty price frame" in message:
        return "missing_market_data"
    if any(
        term in message
        for term in (
            "price timestamps",
            "valid positive ohlc",
            "high",
            "close",
            "open",
            "low",
        )
    ):
        return "invalid_price_data"
    return "validation_error"


def evaluate_symbol_universe(
    frames: dict[str, pd.DataFrame],
    benchmark: pd.Series,
    *,
    initial_capital: float = 100_000.0,
    cost_bps: float = 10.0,
    cost_model: IndiaEquityCostModel | None = None,
    min_train_size: int = 252,
    n_splits: int = 5,
    minimum_observations: int = 300,
) -> pd.DataFrame:
    """Evaluate each symbol independently and preserve failures as explicit rows.

    Frames must contain High, Low, and Close columns. The function does not
    select winners or combine assets into a portfolio; each symbol receives
    its own independent walk-forward evaluation.
    """
    if not frames:
        raise ValueError("frames must contain at least one symbol")
    if minimum_observations < 2:
        raise ValueError("minimum_observations must be at least 2")
    if not benchmark.index.is_unique:
        raise ValueError("benchmark contains duplicate timestamps")
    if not benchmark.index.is_monotonic_increasing:
        benchmark = benchmark.sort_index()
    benchmark = pd.to_numeric(benchmark, errors="coerce")
    benchmark = benchmark.replace([float("inf"), float("-inf")], float("nan"))
    benchmark = benchmark.where(benchmark > 0)

    rows: list[dict[str, float | int | str]] = []
    for symbol, frame in sorted(frames.items()):
        try:
            if frame.empty:
                raise ValueError("empty price frame")
            if not frame.index.is_unique:
                raise ValueError("duplicate price timestamps")
            if not frame.index.is_monotonic_increasing:
                frame = frame.sort_index()
            missing_columns = {"High", "Low", "Close"} - set(frame.columns)
            if missing_columns:
                raise ValueError(f"missing required columns: {sorted(missing_columns)}")
            required = frame[["High", "Low", "Close"]].apply(pd.to_numeric, errors="coerce")
            required = required.replace([float("inf"), float("-inf")], float("nan"))
            required = required.dropna()
            required = required[(required > 0).all(axis=1)]
            valid_ohlc = (
                (required["High"] >= required["Low"])
                & (required["Close"] >= required["Low"])
                & (required["Close"] <= required["High"])
            )
            if "Open" in frame.columns:
                open_prices = pd.to_numeric(frame.loc[required.index, "Open"], errors="coerce")
                valid_ohlc &= (
                    open_prices.notna()
                    & (open_prices >= required["Low"])
                    & (open_prices <= required["High"])
                )
            required = required[valid_ohlc]
            clean_frame = frame.loc[required.index].copy()
            clean_frame[["High", "Low", "Close"]] = required
            if clean_frame.empty:
                raise ValueError("no valid positive OHLC observations")
            aligned_benchmark = benchmark.reindex(clean_frame.index)
            if aligned_benchmark.isna().all():
                raise ValueError("benchmark has no observations aligned to valid price dates")
            signals = generate_pipeline_signals(clean_frame, aligned_benchmark)
            prices = required["Close"].reindex(signals.index)
            valid = pd.concat([prices.rename("price"), signals.rename("signal")], axis=1)
            valid = valid.replace([float("inf"), float("-inf")], float("nan")).dropna()
            if len(valid) < minimum_observations:
                raise ValueError(
                    f"insufficient observations: {len(valid)} < {minimum_observations}"
                )
            folds = walk_forward_evaluate(
                valid["price"],
                valid["signal"],
                initial_capital=initial_capital,
                cost_bps=cost_bps,
                cost_model=cost_model,
                min_train_size=min_train_size,
                n_splits=n_splits,
            )
            for record in folds.to_dict(orient="records"):
                rows.append({"symbol": symbol, "status": "ok", **record})
        except (KeyError, TypeError, ValueError) as exc:
            rows.append(
                {
                    "symbol": symbol,
                    "status": "skipped",
                    "skip_category": _skip_category(str(exc)),
                    "reason": str(exc),
                }
            )
    return pd.DataFrame(rows)
