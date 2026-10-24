from __future__ import annotations

"""
==========================================================
COMPARABLE STATISTICS ENGINE
Module  : statistics
Version : V1.0
==========================================================

Provides statistical analysis of comparable valuation
multiples.

Metrics
-------
• Mean
• Median
• Minimum
• Maximum
• Standard Deviation
• Quartiles (Q1 / Q3)
• Interquartile Range (IQR)
• Trimmed Mean
• Outlier Detection
"""

import statistics
from dataclasses import dataclass

# ==========================================================
# Statistics Result
# ==========================================================


@dataclass(slots=True)
class MultipleStatistics:

    count: int

    minimum: float

    maximum: float

    mean: float

    median: float

    standard_deviation: float

    q1: float

    q3: float

    iqr: float

    trimmed_mean: float

    outliers: list[float]


# ==========================================================
# Percentile
# ==========================================================


def percentile(values: list[float], pct: float) -> float:

    if not values:
        return 0.0

    values = sorted(values)

    k = (len(values) - 1) * pct

    f = int(k)

    c = min(f + 1, len(values) - 1)

    if f == c:
        return values[f]

    d = k - f

    return values[f] * (1 - d) + values[c] * d


# ==========================================================
# Trimmed Mean
# ==========================================================


def calculate_trimmed_mean(
    values: list[float],
    trim_pct: float = 0.10,
) -> float:

    if not values:
        return 0.0

    values = sorted(values)

    trim = int(len(values) * trim_pct)

    if len(values) <= 2 * trim:
        return statistics.mean(values)

    trimmed = values[trim : len(values) - trim]

    return statistics.mean(trimmed)


# ==========================================================
# IQR Outlier Detection
# ==========================================================


def detect_outliers(values: list[float]) -> list[float]:

    if len(values) < 4:
        return []

    q1 = percentile(values, 0.25)

    q3 = percentile(values, 0.75)

    iqr = q3 - q1

    lower = q1 - 1.5 * iqr

    upper = q3 + 1.5 * iqr

    return [value for value in values if value < lower or value > upper]


# ==========================================================
# Main Statistics
# ==========================================================


def compute_statistics(
    values: list[float],
) -> MultipleStatistics:

    if not values:
        raise ValueError("Statistics requires at least one value.")

    q1 = percentile(values, 0.25)

    q3 = percentile(values, 0.75)

    iqr = q3 - q1

    stdev = statistics.stdev(values) if len(values) > 1 else 0.0

    return MultipleStatistics(
        count=len(values),
        minimum=min(values),
        maximum=max(values),
        mean=statistics.mean(values),
        median=statistics.median(values),
        standard_deviation=stdev,
        q1=q1,
        q3=q3,
        iqr=iqr,
        trimmed_mean=calculate_trimmed_mean(values),
        outliers=detect_outliers(values),
    )
