"""Book-aligned time-series mean-reversion diagnostics."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _clean_series(values: pd.Series) -> pd.Series:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    clean = clean[np.isfinite(clean.to_numpy(dtype=float))]
    if len(clean) < 3:
        raise ValueError("at least 3 observations are required")
    return clean.astype(float)


def adf_diagnostic(
    values: pd.Series,
    *,
    lags: int = 1,
) -> dict[str, float | int | None]:
    """Estimate the ADF mean-reversion coefficient and t-statistic.

    This implements the regression form used in the book with a constant
    and optional lagged differences. It reports the ADF statistic but does
    not attach external critical values or p-values.
    """
    if lags < 0:
        raise ValueError("lags must be non-negative")

    clean = _clean_series(values)
    if len(clean) <= lags + 2:
        raise ValueError("not enough observations for the requested lags")

    series = clean.to_numpy()
    delta = np.diff(series)
    rows: list[list[float]] = []
    targets: list[float] = []
    for index in range(lags, len(delta)):
        row = [1.0, series[index]]
        row.extend(delta[index - lag] for lag in range(1, lags + 1))
        rows.append(row)
        targets.append(delta[index])

    x = np.asarray(rows, dtype=float)
    y = np.asarray(targets, dtype=float)
    coefficients, _, _, _ = np.linalg.lstsq(x, y, rcond=None)
    residuals = y - x @ coefficients
    degrees_of_freedom = len(y) - x.shape[1]
    if degrees_of_freedom <= 0:
        raise ValueError("not enough observations for the requested lags")

    residual_variance = float((residuals @ residuals) / degrees_of_freedom)
    covariance = np.linalg.pinv(x.T @ x) * residual_variance
    standard_error = math.sqrt(max(float(covariance[1, 1]), 0.0))
    coefficient = float(coefficients[1])
    statistic = coefficient / standard_error if standard_error > 0.0 else None

    return {
        "observations": int(len(y)),
        "lags": int(lags),
        "lambda": coefficient,
        "adf_statistic": float(statistic) if statistic is not None else None,
    }


def hurst_exponent(
    values: pd.Series,
    *,
    min_lag: int = 2,
    max_lag: int | None = None,
) -> float:
    """Estimate the Hurst exponent from log-log variance scaling."""
    if min_lag < 2:
        raise ValueError("min_lag must be at least 2")

    clean = _clean_series(values)
    if (clean <= 0.0).any():
        raise ValueError("values must be strictly positive for log-price scaling")
    log_values = np.log(clean.to_numpy())
    available_max = max(min(len(log_values) // 2, 100), min_lag)
    selected_max = available_max if max_lag is None else min(max_lag, available_max)
    if selected_max < min_lag:
        raise ValueError("max_lag must be at least min_lag")

    lags = np.arange(min_lag, selected_max + 1)
    variances = np.asarray(
        [
            np.mean(
                (log_values[lag:] - log_values[:-lag]) ** 2,
            )
            for lag in lags
        ],
        dtype=float,
    )
    valid = variances > 0.0
    if valid.sum() < 2:
        raise ValueError("insufficient variation to estimate Hurst exponent")

    slope, _ = np.polyfit(np.log(lags[valid]), np.log(variances[valid]), 1)
    return float(slope / 2.0)


def variance_ratio(
    values: pd.Series,
    *,
    lag: int = 2,
) -> float:
    """Estimate the Lo-style variance ratio at a selected lag."""
    if lag < 2:
        raise ValueError("lag must be at least 2")

    clean = _clean_series(values)
    if (clean <= 0.0).any():
        raise ValueError("values must be strictly positive for log returns")
    log_values = np.log(clean.to_numpy())
    one_step = np.diff(log_values)
    lagged = log_values[lag:] - log_values[:-lag]
    one_variance = float(np.var(one_step, ddof=1))
    if math.isclose(one_variance, 0.0, abs_tol=1e-12):
        raise ValueError("one-step returns must have non-zero variance")

    return float(np.var(lagged, ddof=1) / (lag * one_variance))


def mean_reversion_half_life(values: pd.Series) -> float | None:
    """Estimate the mean-reversion half-life from the lag coefficient."""
    clean = _clean_series(values)
    series = clean.to_numpy()
    lagged = series[:-1]
    delta = np.diff(series)
    x = np.column_stack([np.ones(len(lagged)), lagged])
    coefficients, _, _, _ = np.linalg.lstsq(x, delta, rcond=None)
    coefficient = float(coefficients[1])

    if coefficient >= 0.0:
        return None
    return float(-math.log(2.0) / coefficient)


def mean_reversion_summary(
    values: pd.Series,
    *,
    adf_lags: int = 1,
    variance_ratio_lag: int = 2,
) -> dict[str, float | int | None]:
    """Return the four core Chapter 2 mean-reversion diagnostics."""
    adf = adf_diagnostic(values, lags=adf_lags)
    return {
        "observations": int(adf["observations"]),
        "adf_statistic": adf["adf_statistic"],
        "adf_lambda": adf["lambda"],
        "hurst_exponent": hurst_exponent(values),
        "variance_ratio": variance_ratio(values, lag=variance_ratio_lag),
        "half_life": mean_reversion_half_life(values),
    }
