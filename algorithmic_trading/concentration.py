"""Portfolio concentration: sector weights, effective number of holdings and risk share.

Weight concentration (how much money is where) and risk concentration (where the variance
comes from) differ: a small position in a volatile stock can dominate risk. Pure functions,
no network. The sector map is supplied by the caller (see ``scanner.sectors``).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

import pandas as pd

from algorithmic_trading.risk_metrics import normalise_weights, risk_contributions

SECTOR_LIMIT = 0.40  # one sector above this share of capital is flagged
STOCK_LIMIT = 0.25  # one stock above this share of capital is flagged
RISK_LEADERS = 3
RISK_LEADERS_LIMIT = 0.70  # the top-3 holdings carrying more than this share of variance
EFFECTIVE_N_FRACTION = 0.5  # effective holdings below this share of the actual count


@dataclass(frozen=True)
class ConcentrationReport:
    weights: pd.Series
    sector_weights: pd.Series
    sector_risk: pd.Series
    risk_share: pd.Series
    herfindahl: float
    effective_holdings: float
    flags: list[str] = field(default_factory=list)


def herfindahl(weights: Mapping[str, float] | pd.Series) -> float:
    """Sum of squared weights: 1/N when equal, 1.0 when everything is one stock."""
    w = normalise_weights(weights)
    return float((w**2).sum())


def effective_holdings(weights: Mapping[str, float] | pd.Series) -> float:
    """``1 / HHI``: how many equally weighted stocks would be as concentrated."""
    return 1.0 / herfindahl(weights)


def group_by_sector(
    values: pd.Series, sector_of: Mapping[str, str | None], unmapped: str = "Unmapped"
) -> pd.Series:
    """Sum ``values`` per sector (missing names go to ``unmapped``), largest first."""
    sectors = pd.Series({name: sector_of.get(name) or unmapped for name in values.index})
    return values.groupby(sectors).sum().sort_values(ascending=False)


def concentration_report(
    returns: pd.DataFrame,
    weights: Mapping[str, float] | pd.Series,
    sector_of: Mapping[str, str | None],
) -> ConcentrationReport:
    """Weight and risk concentration for ``weights`` with plain-language flags."""
    w = normalise_weights(weights)
    if w.shape[0] < 2:
        raise ValueError("Need at least two holdings.")
    risk = risk_contributions(returns, w)
    sector_w = group_by_sector(w, sector_of)
    sector_r = group_by_sector(risk, sector_of)
    hhi = herfindahl(w)
    eff = 1.0 / hhi

    flags: list[str] = []
    top_sector, top_sector_w = sector_w.index[0], float(sector_w.iloc[0])
    if top_sector_w > SECTOR_LIMIT and top_sector != "Unmapped":
        flags.append(f"{top_sector} is {top_sector_w:.0%} of capital (limit {SECTOR_LIMIT:.0%}).")
    for name, share in w[w > STOCK_LIMIT].items():
        flags.append(f"{name} is {share:.0%} of capital (limit {STOCK_LIMIT:.0%}).")
    leaders = risk.sort_values(ascending=False).head(RISK_LEADERS)
    if w.shape[0] > RISK_LEADERS and float(leaders.sum()) > RISK_LEADERS_LIMIT:
        flags.append(
            f"{', '.join(leaders.index)} carry {float(leaders.sum()):.0%} of the portfolio's risk."
        )
    if eff < EFFECTIVE_N_FRACTION * w.shape[0]:
        flags.append(f"Weights behave like {eff:.1f} equal holdings, not {w.shape[0]}.")
    unmapped = float(sector_w.get("Unmapped", 0.0))
    if unmapped > 0:
        flags.append(f"{unmapped:.0%} of capital has no sector in the built-in map.")
    return ConcentrationReport(
        weights=w,
        sector_weights=sector_w,
        sector_risk=sector_r,
        risk_share=risk.sort_values(ascending=False),
        herfindahl=hhi,
        effective_holdings=eff,
        flags=flags,
    )
