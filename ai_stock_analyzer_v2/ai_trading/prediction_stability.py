"""Book-aligned prediction stability diagnostics."""

from __future__ import annotations

import pandas as pd


def prediction_stability(probabilities: pd.Series) -> dict[str, float | int | None]:
    """Summarize stability and directional persistence of model probabilities."""
    clean = pd.to_numeric(probabilities, errors="coerce").dropna()
    if clean.empty:
        return {
            "observations": 0,
            "mean_probability": None,
            "probability_std": None,
            "minimum_probability": None,
            "maximum_probability": None,
            "directional_agreement": None,
            "directional_flips": 0,
        }
    if ((clean < 0.0) | (clean > 1.0)).any():
        raise ValueError("probabilities must be between 0 and 1")
    directions = clean.ge(0.5)
    flips = int(directions.astype(int).diff().abs().fillna(0).sum())
    transitions = max(len(directions) - 1, 0)
    agreement = float(1.0 - flips / transitions) if transitions else 1.0
    return {
        "observations": int(len(clean)),
        "mean_probability": float(clean.mean()),
        "probability_std": float(clean.std(ddof=0)),
        "minimum_probability": float(clean.min()),
        "maximum_probability": float(clean.max()),
        "directional_agreement": agreement,
        "directional_flips": flips,
    }


def prediction_stability_report(
    probabilities: pd.Series,
    *,
    max_std: float = 0.10,
) -> dict[str, float | int | bool | None]:
    """Classify a probability series as stable when dispersion stays below a limit."""
    if max_std < 0.0:
        raise ValueError("max_std must be non-negative")
    summary = prediction_stability(probabilities)
    std = summary["probability_std"]
    stable = bool(std is not None and float(std) <= max_std)
    return {**summary, "max_std": float(max_std), "stable": stable}
