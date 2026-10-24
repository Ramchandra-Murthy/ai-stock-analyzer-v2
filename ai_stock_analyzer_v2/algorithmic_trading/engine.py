"""Small orchestration layer for NSE/BSE algorithmic analysis."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from algorithmic_trading.market import MarketSymbol
from algorithmic_trading.regime_engine import classify_regime, regime_score
from algorithmic_trading.relative_strength import relative_return


@dataclass(frozen=True)
class AlgorithmicSignal:
    symbol: str
    exchange: str
    regime: str
    regime_score: int
    relative_return_pct: float | None

    @property
    def direction(self) -> str:
        if self.regime == "BULLISH":
            return "LONG"
        if self.regime == "BEARISH":
            return "SHORT"
        return "FLAT"


def analyze_symbol(
    symbol: MarketSymbol,
    prices: pd.DataFrame,
    benchmark: pd.Series | None = None,
) -> AlgorithmicSignal:
    score = regime_score(prices)
    regime = classify_regime(prices)
    relative = None
    if benchmark is not None:
        relative = relative_return(prices["Close"], benchmark)

    return AlgorithmicSignal(
        symbol=symbol.symbol,
        exchange=symbol.exchange,
        regime=regime,
        regime_score=score,
        relative_return_pct=relative,
    )
