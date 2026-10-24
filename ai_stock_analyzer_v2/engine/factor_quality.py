"""Cross-sectional factor quality diagnostics for research workflows.

Forward returns are outcomes used only for evaluation; this module does not
change signal generation, scanners, portfolio construction, or order handling.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd


def evaluate_factor_quality(
    factor: pd.DataFrame,
    forward_returns: Mapping[int, pd.DataFrame],
    *,
    min_assets: int = 3,
) -> pd.DataFrame:
    """Summarize daily cross-sectional Spearman IC for each forward horizon.

    Both inputs use dates as rows and asset identifiers as columns. Each
    horizon return frame must contain forward returns known only after the
    corresponding date. A date contributes only when at least min_assets
    finite paired observations are available. ICIR is mean daily IC divided
    by its sample standard deviation; it is undefined with fewer than two ICs
    or zero IC standard deviation.
    """
    if not isinstance(factor, pd.DataFrame):
        raise TypeError("factor must be a pandas DataFrame")
    if factor.index.has_duplicates or factor.columns.has_duplicates:
        raise ValueError("factor index and columns must be unique")
    if isinstance(min_assets, bool) or not isinstance(min_assets, int) or min_assets < 2:
        raise ValueError("min_assets must be an integer of at least 2")
    if not isinstance(forward_returns, Mapping) or not forward_returns:
        raise ValueError("forward_returns must be a non-empty horizon mapping")

    horizons = list(forward_returns)
    if any(
        isinstance(horizon, bool) or not isinstance(horizon, (int, np.integer)) or horizon < 1
        for horizon in horizons
    ):
        raise ValueError("forward-return horizons must be positive integers")

    factor_values = factor.apply(pd.to_numeric, errors="coerce")
    rows: list[dict[str, object]] = []
    for horizon, returns in forward_returns.items():
        if not isinstance(returns, pd.DataFrame):
            raise TypeError("each forward-return horizon must contain a DataFrame")
        if returns.index.has_duplicates or returns.columns.has_duplicates:
            raise ValueError("forward-return indexes and columns must be unique")

        dates = factor_values.index.intersection(returns.index, sort=False)
        assets = factor_values.columns.intersection(returns.columns, sort=False)
        daily_ics: list[float] = []
        return_values = returns.apply(pd.to_numeric, errors="coerce")
        for date in dates:
            paired = pd.concat(
                [factor_values.loc[date, assets], return_values.loc[date, assets]],
                axis=1,
            )
            paired = paired.replace([np.inf, -np.inf], np.nan).dropna()
            if len(paired) < min_assets:
                continue
            if paired.iloc[:, 0].nunique() < 2 or paired.iloc[:, 1].nunique() < 2:
                continue
            ic = paired.iloc[:, 0].corr(paired.iloc[:, 1], method="spearman")
            if np.isfinite(ic):
                daily_ics.append(float(ic))

        values = pd.Series(daily_ics, dtype=float)
        mean_ic = float(values.mean()) if not values.empty else np.nan
        std_ic = float(values.std(ddof=1)) if len(values) > 1 else np.nan
        icir = (
            mean_ic / std_ic
            if np.isfinite(mean_ic) and np.isfinite(std_ic) and std_ic > 0
            else np.nan
        )
        rows.append(
            {
                "Horizon": int(horizon),
                "Observations": len(values),
                "Mean IC": mean_ic,
                "IC Std": std_ic,
                "ICIR": icir,
                "Positive IC Rate": float((values > 0).mean()) if not values.empty else np.nan,
            }
        )

    return pd.DataFrame(
        rows,
        columns=["Horizon", "Observations", "Mean IC", "IC Std", "ICIR", "Positive IC Rate"],
    )
