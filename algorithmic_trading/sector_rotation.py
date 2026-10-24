"""Sector-rotation quadrants from relative strength (research only)."""

from __future__ import annotations

import numpy as np
import pandas as pd

QUADRANTS = ("Leading", "Weakening", "Lagging", "Improving")
SECTOR_TICKERS = {
    "Bank": "^NSEBANK",
    "IT": "^CNXIT",
    "FMCG": "^CNXFMCG",
    "Pharma": "^CNXPHARMA",
    "Auto": "^CNXAUTO",
    "Metal": "^CNXMETAL",
    "Energy": "^CNXENERGY",
    "Realty": "^CNXREALTY",
    "Infra": "^CNXINFRA",
    "Financial services": "^CNXFIN",
}
BENCHMARK_TICKER = "^NSEI"


def relative_strength_ratio(price: pd.Series, benchmark: pd.Series) -> pd.Series:
    """Price relative to the benchmark, rebased to 100 at the first common bar."""
    both = pd.concat([price, benchmark], axis=1, join="inner").dropna()
    if len(both) < 2 or (both <= 0).any().any():
        raise ValueError("Need at least two positive aligned prices.")
    ratio = both.iloc[:, 0] / both.iloc[:, 1]
    return 100.0 * ratio / ratio.iloc[0]


def rrg_point(
    ratio: pd.Series, ratio_window: int = 63, momentum_window: int = 21
) -> tuple[float, float]:
    """(RS-ratio, RS-momentum), both centred on 100, using only data up to the last bar.

    RS-ratio: current relative strength vs its own ``ratio_window`` average.
    RS-momentum: that RS-ratio vs its value ``momentum_window`` bars ago.
    """
    rs = 100.0 * ratio / ratio.rolling(ratio_window, min_periods=ratio_window).mean()
    mom = 100.0 * rs / rs.shift(momentum_window)
    if pd.isna(rs.iloc[-1]) or pd.isna(mom.iloc[-1]):
        raise ValueError("Not enough history for the chosen windows.")
    return float(rs.iloc[-1]), float(mom.iloc[-1])


def quadrant(rs_ratio: float, rs_momentum: float) -> str:
    if rs_ratio >= 100:
        return "Leading" if rs_momentum >= 100 else "Weakening"
    return "Improving" if rs_momentum >= 100 else "Lagging"


def sector_table(
    prices: pd.DataFrame, benchmark: pd.Series, windows: tuple[int, ...] = (21, 63, 126, 252)
) -> pd.DataFrame:
    """Trailing returns, excess return vs benchmark and RRG quadrant per column."""
    rows = []
    for name in prices.columns:
        series = prices[name].dropna()
        try:
            ratio = relative_strength_ratio(series, benchmark)
            rs, mom = rrg_point(ratio)
        except ValueError:
            continue
        row: dict[str, object] = {"Sector": name}
        for w in windows:
            if len(series) > w and len(benchmark.dropna()) > w:
                row[f"{w}d return"] = float(series.iloc[-1] / series.iloc[-1 - w] - 1.0)
                b = benchmark.dropna()
                row[f"{w}d vs index"] = row[f"{w}d return"] - float(
                    b.iloc[-1] / b.iloc[-1 - w] - 1.0
                )
            else:
                row[f"{w}d return"] = row[f"{w}d vs index"] = np.nan
        row.update({"RS ratio": rs, "RS momentum": mom, "Quadrant": quadrant(rs, mom)})
        rows.append(row)
    if not rows:
        raise ValueError("No sector had enough aligned history.")
    return pd.DataFrame(rows).set_index("Sector").sort_values("RS ratio", ascending=False)
