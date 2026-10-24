"""Book-aligned time-series momentum diagnostics."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _validate_periods(periods: tuple[int, ...], name: str) -> None:
    if not periods:
        raise ValueError(f"{name} must contain at least one period")
    if any(period < 1 for period in periods):
        raise ValueError(f"{name} values must be at least 1")


def time_series_momentum_diagnostics(
    returns: pd.Series,
    *,
    lookbacks: tuple[int, ...] = (5, 20, 60),
    holding_periods: tuple[int, ...] = (1, 5, 20),
) -> pd.DataFrame:
    """Measure past/future return and sign correlations across horizons.

    For each lookback and holding period, the past return is the compounded
    return over the lookback ending immediately before the future window.
    The future return is the compounded return over the selected holding
    period. Positive correlation is evidence consistent with time-series
    momentum, not a trading guarantee.
    """
    _validate_periods(lookbacks, "lookbacks")
    _validate_periods(holding_periods, "holding_periods")

    numeric = pd.to_numeric(returns, errors="coerce")
    clean = numeric[np.isfinite(numeric.to_numpy(dtype=float))].astype(float)
    if (clean <= -1.0).any():
        raise ValueError("returns must be greater than -1.0")
    rows: list[dict[str, float | int | None]] = []
    for lookback in lookbacks:
        for holding in holding_periods:
            start = lookback
            stop = len(clean) - holding + 1
            if stop <= start:
                rows.append(
                    {
                        "lookback": int(lookback),
                        "holding_period": int(holding),
                        "observations": 0,
                        "return_correlation": None,
                        "sign_correlation": None,
                    }
                )
                continue

            values = clean.to_numpy()
            past = np.asarray(
                [
                    np.prod(1.0 + values[index - lookback : index]) - 1.0
                    for index in range(start, stop)
                ]
            )
            future = np.asarray(
                [
                    np.prod(1.0 + values[index : index + holding]) - 1.0
                    for index in range(start, stop)
                ]
            )
            finite_windows = np.isfinite(past) & np.isfinite(future)
            past = past[finite_windows]
            future = future[finite_windows]

            return_correlation = (
                float(np.corrcoef(past, future)[0, 1])
                if len(past) > 1
                and not math.isclose(float(np.std(past)), 0.0, abs_tol=1e-12)
                and not math.isclose(float(np.std(future)), 0.0, abs_tol=1e-12)
                else None
            )
            past_sign = np.sign(past)
            future_sign = np.sign(future)
            sign_correlation = (
                float(np.corrcoef(past_sign, future_sign)[0, 1])
                if len(past_sign) > 1
                and not math.isclose(float(np.std(past_sign)), 0.0, abs_tol=1e-12)
                and not math.isclose(float(np.std(future_sign)), 0.0, abs_tol=1e-12)
                else None
            )
            rows.append(
                {
                    "lookback": int(lookback),
                    "holding_period": int(holding),
                    "observations": int(len(past)),
                    "return_correlation": return_correlation,
                    "sign_correlation": sign_correlation,
                }
            )

    return pd.DataFrame(rows)


def best_time_series_momentum_pair(
    returns: pd.Series,
    *,
    lookbacks: tuple[int, ...] = (5, 20, 60),
    holding_periods: tuple[int, ...] = (1, 5, 20),
) -> dict[str, float | int | None]:
    """Return the horizon pair with the strongest positive return correlation."""
    report = time_series_momentum_diagnostics(
        returns,
        lookbacks=lookbacks,
        holding_periods=holding_periods,
    )
    valid = report.dropna(subset=["return_correlation"])
    if valid.empty:
        return {
            "lookback": None,
            "holding_period": None,
            "return_correlation": None,
            "sign_correlation": None,
        }

    row = valid.loc[valid["return_correlation"].idxmax()]
    return {
        "lookback": int(row["lookback"]),
        "holding_period": int(row["holding_period"]),
        "return_correlation": float(row["return_correlation"]),
        "sign_correlation": (
            float(row["sign_correlation"]) if pd.notna(row["sign_correlation"]) else None
        ),
    }
