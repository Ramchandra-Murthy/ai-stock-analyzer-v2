import pandas as pd

from algorithmic_trading.pipeline import analyze_symbol


def _frame():
    index = pd.date_range("2026-01-01", periods=60, freq="D")
    close = pd.Series(range(100, 160), index=index, dtype=float)
    return pd.DataFrame(
        {
            "High": close + 2,
            "Low": close - 2,
            "Close": close,
        }
    )


def test_long_signal_uses_atr_stop_for_nonzero_position_size(monkeypatch):
    monkeypatch.setattr(
        "algorithmic_trading.pipeline.regime_score",
        lambda frame: 3,
    )
    monkeypatch.setattr(
        "algorithmic_trading.pipeline.classify_regime",
        lambda frame: "BULLISH",
    )
    result = analyze_symbol(
        "AAA",
        _frame(),
        benchmark=None,
        capital=100_000,
        risk_fraction=0.01,
    )
    assert result.signal.direction == "LONG"
    assert result.position_size.quantity > 0
    assert result.position_size.risk_per_share > 0


def test_flat_signal_does_not_create_position(monkeypatch):
    monkeypatch.setattr(
        "algorithmic_trading.pipeline.regime_score",
        lambda frame: 0,
    )
    monkeypatch.setattr(
        "algorithmic_trading.pipeline.classify_regime",
        lambda frame: "INCONCLUSIVE",
    )
    frame = _frame()
    result = analyze_symbol(
        "AAA",
        frame,
        benchmark=None,
        capital=100_000,
        risk_fraction=0.01,
    )
    assert result.signal.direction == "FLAT"
    assert result.position_size.quantity == 0
