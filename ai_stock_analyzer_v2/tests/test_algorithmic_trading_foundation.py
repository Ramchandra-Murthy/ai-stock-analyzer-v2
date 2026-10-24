import pandas as pd

from algorithmic_trading.market import make_market_symbol
from algorithmic_trading.position_sizing import atr_position_size
from algorithmic_trading.regime_engine import classify_regime, regime_score
from algorithmic_trading.relative_strength import relative_return


def sample_frame(rows: int = 80) -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=rows, freq="D")
    close = pd.Series(range(100, 100 + rows), index=index, dtype=float)
    return pd.DataFrame(
        {
            "Open": close - 1,
            "High": close + 1,
            "Low": close - 2,
            "Close": close,
            "Volume": 100_000,
        },
        index=index,
    )


def test_nse_and_bse_symbol_adapters() -> None:
    assert make_market_symbol("RELIANCE", "NSE").yfinance_symbol == "RELIANCE.NS"
    assert make_market_symbol("500325", "BSE").yfinance_symbol == "500325.BO"


def test_bullish_regime_and_score() -> None:
    frame = sample_frame()
    assert classify_regime(frame) == "BULLISH"
    assert regime_score(frame) >= 3


def test_relative_return() -> None:
    frame = sample_frame()
    benchmark = pd.Series(range(100, 180), index=frame.index, dtype=float)
    assert relative_return(frame["Close"], benchmark, periods=20) is not None


def test_atr_position_size() -> None:
    assert atr_position_size(100_000, 0.01, 1_000, 10, 1.5) == 66
