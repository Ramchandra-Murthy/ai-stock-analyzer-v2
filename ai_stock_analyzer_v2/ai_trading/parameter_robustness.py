"""Parameter-sweep robustness diagnostics for strategy research.

These summaries describe the distribution across tested configurations; they
do not select a live-trading configuration or correct for all forms of
multiple-testing bias.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def parameter_robustness_summary(
    results: pd.DataFrame,
    *,
    metric_column: str = "sharpe_ratio",
    parameter_columns: tuple[str, ...] | list[str] = (),
    near_best_tolerance: float = 0.10,
) -> dict[str, float | int | None]:
    """Summarize metric stability across tested parameter configurations.

    The metric is assumed to be maximized. Near-best configurations are those
    within the tolerance fraction of the best metric, scaled by its absolute
    magnitude (with a small floor for metrics near zero).
    """
    if not 0.0 <= near_best_tolerance < 1.0:
        raise ValueError("near_best_tolerance must be in [0, 1)")
    if metric_column not in results.columns:
        raise KeyError(f"missing metric column: {metric_column}")

    missing = sorted(set(parameter_columns).difference(results.columns))
    if missing:
        raise KeyError(f"missing parameter columns: {missing}")

    metrics = pd.to_numeric(results[metric_column], errors="coerce")
    valid = metrics.notna() & np.isfinite(metrics.to_numpy(dtype=float))
    if parameter_columns:
        valid &= results[list(parameter_columns)].notna().all(axis=1)
    clean = metrics.loc[valid].astype(float)

    if clean.empty:
        return {
            "configurations": 0,
            "best_metric": None,
            "median_metric": None,
            "metric_std": None,
            "positive_fraction": None,
            "near_best_fraction": None,
            "near_best_threshold": None,
        }

    best = float(clean.max())
    scale = max(abs(best), 1e-12)
    threshold = best - near_best_tolerance * scale
    return {
        "configurations": int(len(clean)),
        "best_metric": best,
        "median_metric": float(clean.median()),
        "metric_std": float(clean.std(ddof=1)) if len(clean) > 1 else 0.0,
        "positive_fraction": float((clean > 0.0).mean()),
        "near_best_fraction": float((clean >= threshold).mean()),
        "near_best_threshold": float(threshold),
    }
