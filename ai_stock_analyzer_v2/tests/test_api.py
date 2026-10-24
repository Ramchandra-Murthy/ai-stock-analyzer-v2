import pandas as pd

from api.main import dashboard, health, options_chain
from services.options_analytics import OptionChainResult


def test_health():
    assert health() == {"status": "ok", "service": "eros-api"}


def test_dashboard_path():
    response = dashboard()
    assert str(response.path).replace("\\", "/").endswith("api/static/index.html")


def test_intraday_health_without_scan(monkeypatch):
    monkeypatch.setattr("api.main.recent_scans", lambda limit: [])
    from api.main import intraday_health

    result = intraday_health()
    assert result["status"] == "NO_SCAN"
    assert result["candidates"] == 0


def test_options_chain_returns_normalized_analytics(monkeypatch):
    chain = pd.DataFrame(
        {
            "strike": [25000.0],
            "CE LTP": [100.0],
            "CE volume": [1000.0],
            "CE OI": [20000.0],
            "CE OI change": [500.0],
            "CE IV": [14.0],
            "PE LTP": [110.0],
            "PE volume": [1200.0],
            "PE OI": [22000.0],
            "PE OI change": [700.0],
            "PE IV": [15.0],
            "PCR OI": [1.1],
        }
    )
    result = OptionChainResult(
        "NIFTY",
        "NSE:NIFTY",
        "29-Sep-2026",
        25050.0,
        chain,
        ("29-Sep-2026", "06-Oct-2026"),
        "AVAILABLE",
        "Option chain loaded from NSE.",
    )
    monkeypatch.setattr("api.main.fetch_option_chain", lambda underlying, expiry: result)

    payload = options_chain("NIFTY", "29-Sep-2026")

    assert payload["status"] == "AVAILABLE"
    assert payload["provider"] == "NSE:NIFTY"
    assert payload["spot"] == 25050.0
    assert payload["expiries"] == ["29-Sep-2026", "06-Oct-2026"]
    assert payload["chain"][0]["strike"] == 25000.0
    assert payload["summary"][2]["Metric"] == "PCR (OI)"


def test_options_chain_rejects_unavailable_expiry(monkeypatch):
    result = OptionChainResult(
        "NIFTY",
        "NSE:NIFTY",
        "29-Sep-2026",
        25050.0,
        pd.DataFrame(),
        ("29-Sep-2026", "06-Oct-2026"),
        "AVAILABLE",
        "Option chain loaded from NSE.",
    )
    monkeypatch.setattr("api.main.fetch_option_chain", lambda underlying, expiry: result)

    try:
        options_chain("NIFTY", "30-Oct-2026")
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 400
    else:
        raise AssertionError("Expected unavailable expiry to be rejected")
