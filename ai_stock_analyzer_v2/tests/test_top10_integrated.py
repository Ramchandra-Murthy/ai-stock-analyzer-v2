import pandas as pd

from scanner.top10_integrated import scan_top10_integrated


def test_scan_top10_integrated_returns_ranked_movers(monkeypatch) -> None:
    monkeypatch.setattr(
        "scanner.top10_integrated.NSE_CANDIDATES",
        ["RELIANCE"],
    )
    monkeypatch.setattr(
        "scanner.top10_integrated.BSE_CANDIDATES",
        [],
    )
    monkeypatch.setattr(
        "scanner.top10_integrated._batch_change_screen",
        lambda candidates: [("RELIANCE.NS", "NSE", 4.5)],
    )
    monkeypatch.setattr(
        "scanner.top10_integrated.scan_integrated_tickers",
        lambda tickers, period, interval: pd.DataFrame(
            [
                {
                    "Ticker": tickers[0],
                    "Close": 1500.0,
                    "Regime": "BULLISH",
                    "Regime Score": 1.0,
                    "Edge Signal": 1.0,
                    "Direction": "LONG",
                }
            ]
        ),
    )

    result = scan_top10_integrated()

    assert result.iloc[0]["Ticker"] == "RELIANCE.NS"
    assert result.iloc[0]["Change %"] == 4.5
    assert result.iloc[0]["Direction"] == "LONG"
