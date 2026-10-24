import pandas as pd
import pytest

from algorithmic_trading.pipeline import analyze_symbol


def _market_frame() -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=80, freq="D")
    close = pd.Series(range(100, 180), index=index, dtype=float)
    return pd.DataFrame(
        {
            "Open": close,
            "High": close + 1,
            "Low": close - 1,
            "Close": close,
            "Volume": 100_000,
        }
    )


def test_pipeline_combines_algorithmic_components() -> None:
    frame = _market_frame()
    benchmark = pd.Series(
        range(100, 140),
        index=pd.date_range("2026-01-01", periods=40, freq="2D"),
        dtype=float,
    )
    trade_returns = pd.Series([0.02, -0.01, 0.03, 0.01])

    result = analyze_symbol(
        "RELIANCE",
        frame,
        benchmark,
        capital=100_000,
        risk_fraction=0.01,
        stop_price=175,
        historical_trade_returns=trade_returns,
    )

    assert result.symbol == "RELIANCE"
    assert result.regime in {"BULLISH", "BEARISH", "INCONCLUSIVE"}
    assert result.signal.direction in {"LONG", "SHORT", "FLAT"}
    assert result.edge is not None
    assert result.position_size.quantity >= 0


def test_pipeline_rejects_missing_close() -> None:
    with pytest.raises(ValueError, match="Close"):
        analyze_symbol(
            "TCS",
            pd.DataFrame({"Open": [100.0]}),
            None,
            capital=100_000,
        )
