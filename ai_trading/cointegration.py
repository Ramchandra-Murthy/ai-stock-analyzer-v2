"""Book-aligned CADF and Johansen cointegration diagnostics."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from ai_trading.mean_reversion import adf_diagnostic, mean_reversion_half_life


def _clean_pair(
    dependent: pd.Series,
    independent: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    frame = pd.concat([dependent, independent], axis=1)
    frame = frame.apply(pd.to_numeric, errors="coerce").dropna()
    finite_rows = np.isfinite(frame.to_numpy(dtype=float)).all(axis=1)
    frame = frame.loc[finite_rows]
    if len(frame) < 4:
        raise ValueError("at least 4 aligned observations are required")
    return frame.iloc[:, 0].astype(float), frame.iloc[:, 1].astype(float)


def cadf_diagnostic(
    dependent: pd.Series,
    independent: pd.Series,
    *,
    lags: int = 1,
) -> dict[str, float | int | None]:
    """Estimate a CADF residual and run the ADF diagnostic on that spread."""
    if lags < 0:
        raise ValueError("lags must be non-negative")

    y, x = _clean_pair(dependent, independent)
    x_matrix = np.column_stack([np.ones(len(x)), x.to_numpy()])
    coefficients, _, _, _ = np.linalg.lstsq(x_matrix, y.to_numpy(), rcond=None)
    residual = y.to_numpy() - x_matrix @ coefficients
    residual_series = pd.Series(residual, index=y.index, name="spread")
    adf = adf_diagnostic(residual_series, lags=lags)

    return {
        "observations": int(len(residual_series)),
        "hedge_ratio": float(coefficients[1]),
        "intercept": float(coefficients[0]),
        "adf_statistic": adf["adf_statistic"],
        "adf_lambda": adf["lambda"],
        "half_life": mean_reversion_half_life(residual_series),
    }


def _residualize(
    values: np.ndarray,
    controls: np.ndarray,
) -> np.ndarray:
    coefficients, _, _, _ = np.linalg.lstsq(controls, values, rcond=None)
    return values - controls @ coefficients


def johansen_diagnostic(
    prices: pd.DataFrame,
    *,
    lags: int = 1,
) -> dict[str, object]:
    """Estimate Johansen eigenvalues, trace/max statistics and hedge vectors.

    The implementation reports likelihood-ratio statistics and eigenvectors
    but intentionally does not attach critical values or infer a cointegration
    rank without an external critical-value table.
    """
    if lags < 1:
        raise ValueError("lags must be non-negative")

    frame = prices.apply(pd.to_numeric, errors="coerce").dropna()
    finite_rows = np.isfinite(frame.to_numpy(dtype=float)).all(axis=1)
    frame = frame.loc[finite_rows]
    if frame.shape[0] <= lags + 2:
        raise ValueError("not enough observations for the requested lags")
    if frame.shape[1] < 2:
        raise ValueError("at least two price series are required")

    values = frame.to_numpy(dtype=float)
    all_differences = np.diff(values, axis=0)
    all_lagged_levels = values[:-1]
    start = lags - 1
    differences = all_differences[start:]
    y_lag = all_lagged_levels[start:]

    controls = [np.ones(len(differences))]
    controls.extend(
        all_differences[start - lag : len(all_differences) - lag] for lag in range(1, lags)
    )
    control_matrix = np.column_stack(controls)

    residual_differences = _residualize(differences, control_matrix)
    residual_levels = _residualize(y_lag, control_matrix)
    n_obs = len(residual_differences)

    s00 = residual_differences.T @ residual_differences / n_obs
    s11 = residual_levels.T @ residual_levels / n_obs
    s01 = residual_differences.T @ residual_levels / n_obs
    s10 = s01.T

    inv_s00 = np.linalg.pinv(s00)
    inv_s11 = np.linalg.pinv(s11)
    eigen_matrix = inv_s11 @ s10 @ inv_s00 @ s01
    eigenvalues, eigenvectors = np.linalg.eig(eigen_matrix)
    order = np.argsort(eigenvalues.real)[::-1]
    eigenvalues = np.clip(eigenvalues.real[order], 0.0, 1.0 - 1e-12)
    eigenvectors = eigenvectors.real[:, order]

    for column in range(eigenvectors.shape[1]):
        norm = np.linalg.norm(eigenvectors[:, column])
        if not math.isclose(norm, 0.0, abs_tol=1e-12):
            eigenvectors[:, column] /= norm

    trace_statistics = [
        float(-n_obs * np.sum(np.log1p(-eigenvalues[index:]))) for index in range(len(eigenvalues))
    ]
    max_statistics = [
        float(-n_obs * math.log1p(-eigenvalues[index])) for index in range(len(eigenvalues))
    ]

    return {
        "observations": int(n_obs),
        "series": int(frame.shape[1]),
        "eigenvalues": eigenvalues.tolist(),
        "trace_statistics": trace_statistics,
        "max_eigen_statistics": max_statistics,
        "eigenvectors": eigenvectors.tolist(),
    }
