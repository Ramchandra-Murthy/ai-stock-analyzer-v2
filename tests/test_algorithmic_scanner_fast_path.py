import pandas as pd

from algorithmic_trading import algorithmic_scanner


def test_scan_universe_uses_bounded_batch_download(monkeypatch):
    calls = {}

    symbol_frame = pd.DataFrame(
        {"Close": [100.0, 101.0, 102.0]},
        index=pd.date_range("2026-01-01", periods=3),
    )
    benchmark_frame = pd.DataFrame(
        {"Close": [100.0, 100.5, 101.0]},
        index=pd.date_range("2026-01-01", periods=3),
    )

    def fake_download(tickers, **kwargs):
        calls["tickers"] = list(tickers)
        calls["kwargs"] = kwargs
        return {
            "AAA.NS": symbol_frame,
            "^NSEI": benchmark_frame,
        }, {}

    monkeypatch.setattr(
        algorithmic_scanner,
        "download_market_frames",
        fake_download,
    )

    monkeypatch.setattr(
        algorithmic_scanner,
        "analyze_symbol",
        lambda **kwargs: type(
            "Analysis",
            (),
            {
                "symbol": "AAA",
                "regime": "BULLISH",
                "regime_score": 2,
                "relative_return_pct": 1.0,
                "signal": type("Signal", (), {"direction": "LONG", "score": 60.0})(),
                "position_size": type(
                    "PositionSize",
                    (),
                    {"quantity": 10, "risk_budget": 1000.0},
                )(),
            },
        )(),
    )

    result = algorithmic_scanner.scan_universe(
        symbols=["AAA"],
        exchange="NSE",
        capital=100_000,
    )

    assert not result.empty
    assert calls["kwargs"] == {
        "period": "1y",
        "interval": "1d",
        "auto_adjust": False,
        "batch_size": 50,
        "timeout": 5.0,
        "retries": 0,
        "recover_missing": False,
    }
    assert calls["tickers"] == ["AAA.NS", "^NSEI"]
