"""Forward-return diagnostics for evaluating classified market regimes.

This is an ex-post research diagnostic: forward returns are outcomes, never inputs
to the regime classifier. Results do not establish predictive power or profitability.
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd


def validate_market_regimes(
    close: pd.Series,
    regimes: pd.Series,
    *,
    horizons: Iterable[int] = (5, 20),
) -> pd.DataFrame:
    """Summarize forward returns by regime and horizon using aligned observations.

    Regimes must be BULLISH, BEARISH, RANGE / MIXED, or INSUFFICIENT DATA.
    Forward returns are simple close-to-close returns. The final horizon rows
    are omitted for each horizon because their outcomes are not yet observable.
    Directional hit rate is undefined for neutral regimes.
    """
    if not isinstance(close, pd.Series) or not isinstance(regimes, pd.Series):
        raise TypeError("close and regimes must be pandas Series")
    if close.index.has_duplicates or regimes.index.has_duplicates:
        raise ValueError("close and regimes must have unique indexes")
    if not close.index.is_monotonic_increasing or not regimes.index.is_monotonic_increasing:
        raise ValueError("close and regimes indexes must be chronological")

    horizon_values = tuple(horizons)
    if not horizon_values or any(
        isinstance(horizon, bool) or not isinstance(horizon, (int, np.integer)) or horizon < 1
        for horizon in horizon_values
    ):
        raise ValueError("horizons must contain positive integers")
    if len(set(horizon_values)) != len(horizon_values):
        raise ValueError("horizons must be unique")

    aligned = pd.concat(
        [
            pd.to_numeric(close, errors="coerce").rename("close"),
            regimes.rename("regime"),
        ],
        axis=1,
        join="inner",
    )
    aligned["close"] = aligned["close"].where(
        np.isfinite(aligned["close"]) & aligned["close"].gt(0)
    )
    allowed = {"BULLISH", "BEARISH", "RANGE / MIXED", "INSUFFICIENT DATA"}
    invalid = aligned["regime"].notna() & ~aligned["regime"].isin(allowed)
    if invalid.any():
        raise ValueError("regimes contain unsupported labels")

    rows: list[dict[str, object]] = []
    for horizon in horizon_values:
        forward_return = aligned["close"].shift(-horizon).div(aligned["close"]).sub(1)
        valid = (
            aligned["close"].notna()
            & aligned["regime"].isin(allowed - {"INSUFFICIENT DATA"})
            & forward_return.notna()
            & np.isfinite(forward_return)
        )
        for regime in ("BULLISH", "BEARISH", "RANGE / MIXED"):
            values = forward_return.loc[valid & aligned["regime"].eq(regime)]
            if regime == "BULLISH" and not values.empty:
                hit_rate = float((values > 0).mean())
            elif regime == "BEARISH" and not values.empty:
                hit_rate = float((values < 0).mean())
            else:
                hit_rate = np.nan
            rows.append(
                {
                    "Regime": regime,
                    "Horizon": int(horizon),
                    "Observations": int(values.count()),
                    "Mean forward return": float(values.mean()) if not values.empty else np.nan,
                    "Median forward return": float(values.median()) if not values.empty else np.nan,
                    "Directional hit rate": hit_rate,
                }
            )
    return pd.DataFrame(
        rows,
        columns=[
            "Regime",
            "Horizon",
            "Observations",
            "Mean forward return",
            "Median forward return",
            "Directional hit rate",
        ],
    )
