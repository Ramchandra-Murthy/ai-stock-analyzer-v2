"""Research-only rolling z-score mean-reversion signal workflow."""

from __future__ import annotations

import numpy as np
import pandas as pd


def mean_reversion_signals(
    spread: pd.Series,
    *,
    lookback: int = 20,
    entry_z: float = 2.0,
    exit_z: float = 0.5,
) -> pd.DataFrame:
    """Build causal long/short spread signals and next-bar positions.

    Rolling statistics use observations available at each timestamp.
    The position column is shifted one row to model next-bar alignment.

    Position values are +1 (long spread), -1 (short spread), or 0 (flat).
    """
    if lookback < 2:
        raise ValueError("lookback must be at least 2")
    if not np.isfinite(entry_z) or entry_z <= 0.0:
        raise ValueError("entry_z must be finite and positive")
    if not np.isfinite(exit_z) or exit_z < 0.0 or exit_z >= entry_z:
        raise ValueError("exit_z must be finite and in [0, entry_z)")

    numeric = pd.to_numeric(spread, errors="coerce")
    clean = numeric.where(np.isfinite(numeric.to_numpy(dtype=float)))
    rolling_mean = clean.rolling(lookback, min_periods=lookback).mean()
    rolling_std = clean.rolling(lookback, min_periods=lookback).std(ddof=1)
    zscore = (clean - rolling_mean) / rolling_std.replace(0.0, np.nan)

    raw_position = np.zeros(len(clean), dtype=int)
    current = 0
    z_values = zscore.to_numpy(dtype=float)
    for index, z_value in enumerate(z_values):
        if not np.isfinite(z_value):
            current = 0
        elif current == 0:
            if z_value <= -entry_z:
                current = 1
            elif z_value >= entry_z:
                current = -1
        elif abs(z_value) <= exit_z:
            current = 0
        raw_position[index] = current

    return pd.DataFrame(
        {
            "spread": clean,
            "rolling_mean": rolling_mean,
            "rolling_std": rolling_std,
            "zscore": zscore,
            "signal": raw_position,
            "position": pd.Series(raw_position, index=clean.index).shift(1).fillna(0).astype(int),
        },
        index=clean.index,
    )
