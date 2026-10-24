"""Tests for the options analytics foundation."""

import pandas as pd

from services.options_analytics import fetch_option_chain, summarize_option_chain


def test_summarize_option_chain_calculates_pcr_and_oi_levels():
    chain = pd.DataFrame(
        {
            "strike": [24900, 25000, 25100],
            "CE LTP": [150.0, 100.0, 60.0],
            "CE volume": [1000, 2000, 1500],
            "CE OI": [10000, 20000, 30000],
            "CE OI change": [500, 1000, 1500],
            "CE IV": [0.18, 0.17, 0.19],
            "PE LTP": [50.0, 100.0, 160.0],
            "PE volume": [1200, 2200, 1800],
            "PE OI": [30000, 25000, 15000],
            "PE OI change": [1000, 1200, 800],
            "PE IV": [0.19, 0.18, 0.17],
            "PCR OI": [3.0, 1.25, 0.5],
        }
    )

    summary = summarize_option_chain(chain)
    values = dict(zip(summary["Metric"], summary["Value"], strict=True))

    assert values["Call OI"] == 60000.0
    assert values["Put OI"] == 70000.0
    assert values["PCR (OI)"] == 70000 / 60000
    assert values["Highest Call OI strike"] == 25100.0
    assert values["Highest Put OI strike"] == 24900.0


def test_empty_chain_has_stable_summary_schema():
    summary = summarize_option_chain(pd.DataFrame())
    assert list(summary.columns) == ["Metric", "Value"]
    assert summary.empty


def test_fetch_option_chain_prefers_nse(monkeypatch):
    payload = {
        "records": {
            "expiryDates": ["29-Sep-2026", "06-Oct-2026"],
            "underlyingValue": 23140.5,
            "data": [
                {
                    "strikePrice": 23100,
                    "expiryDate": "29-Sep-2026",
                    "CE": {
                        "lastPrice": 120.0,
                        "totalTradedVolume": 1000,
                        "openInterest": 20000,
                        "changeinOpenInterest": 1500,
                        "impliedVolatility": 14.2,
                    },
                    "PE": {
                        "lastPrice": 95.0,
                        "totalTradedVolume": 1200,
                        "openInterest": 22000,
                        "changeinOpenInterest": 1700,
                        "impliedVolatility": 15.1,
                    },
                }
            ],
        }
    }

    monkeypatch.setattr(
        "services.options_analytics._fetch_nse_option_chain",
        lambda underlying: payload,
    )

    result = fetch_option_chain("NIFTY")
    assert result.status == "AVAILABLE"
    assert result.provider_symbol == "NSE:NIFTY"
    assert result.expiry == "29-Sep-2026"
    assert result.spot == 23140.5
    assert result.chain.loc[0, "CE OI"] == 20000
    assert result.chain.loc[0, "PE OI"] == 22000


def test_fetch_option_chain_can_reload_requested_nse_expiry(monkeypatch):
    payload = {
        "records": {
            "expiryDates": ["29-Sep-2026", "06-Oct-2026"],
            "underlyingValue": 23140.5,
            "data": [
                {
                    "strikePrice": 23200,
                    "expiryDate": "06-Oct-2026",
                    "CE": {"lastPrice": 80.0, "openInterest": 30000},
                    "PE": {"lastPrice": 110.0, "openInterest": 25000},
                }
            ],
        }
    }

    monkeypatch.setattr(
        "services.options_analytics._fetch_nse_option_chain",
        lambda underlying, expiry=None: payload,
    )

    result = fetch_option_chain("NIFTY", "06-Oct-2026")
    assert result.status == "AVAILABLE"
    assert result.expiry == "06-Oct-2026"
    assert result.chain.loc[0, "strike"] == 23200


def test_fetch_option_chain_prefers_dhan(monkeypatch):
    payload = {
        "data": {
            "last_price": 25123.5,
            "oc": {
                "25100.000000": {
                    "ce": {
                        "last_price": 125.0,
                        "volume": 10000,
                        "oi": 200000,
                        "previous_oi": 180000,
                        "implied_volatility": 12.5,
                    },
                    "pe": {
                        "last_price": 110.0,
                        "volume": 12000,
                        "oi": 220000,
                        "previous_oi": 200000,
                        "implied_volatility": 13.5,
                    },
                }
            },
        },
        "status": "success",
    }

    def fake_dhan(underlying, expiry=None):
        from services.options_analytics import _normalize_dhan_chain

        return _normalize_dhan_chain(
            payload,
            underlying,
            "2026-10-08",
            ("2026-10-08", "2026-10-15"),
        )

    monkeypatch.setattr(
        "services.options_analytics._fetch_dhan_option_chain",
        fake_dhan,
    )
    monkeypatch.setattr(
        "services.options_analytics._fetch_nse_option_chain",
        lambda underlying: (_ for _ in ()).throw(
            AssertionError("NSE should not be called when Dhan succeeds")
        ),
    )

    result = fetch_option_chain("NIFTY")
    assert result.status == "AVAILABLE"
    assert result.provider_symbol == "Dhan:NIFTY"
    assert result.expiry == "2026-10-08"
    assert result.spot == 25123.5
    assert result.chain.loc[0, "CE OI"] == 200000
    assert result.chain.loc[0, "CE OI change"] == 20000
    assert result.chain.loc[0, "PE OI change"] == 20000


def test_dhan_option_chain_converts_display_expiry_to_iso(monkeypatch):
    calls = []

    monkeypatch.setattr(
        "services.options_analytics._fetch_dhan_expiries",
        lambda underlying: ("2026-10-08", "2026-10-15"),
    )

    class FakeClient:
        def option_chain(self, security_id, segment, expiry):
            calls.append((security_id, segment, expiry))
            return {
                "status": "success",
                "data": {
                    "last_price": 25100.0,
                    "oc": {
                        "25100.000000": {
                            "ce": {"last_price": 100, "oi": 10, "volume": 20},
                            "pe": {"last_price": 90, "oi": 12, "volume": 30},
                        }
                    },
                },
            }

    monkeypatch.setattr(
        "services.options_analytics.DhanCredentials.from_env",
        lambda: object(),
    )
    monkeypatch.setattr(
        "services.options_analytics.DhanMarketData",
        lambda credentials: FakeClient(),
    )

    result = __import__(
        "services.options_analytics", fromlist=["_fetch_dhan_option_chain"]
    )._fetch_dhan_option_chain(
        "NIFTY",
        "08-Oct-2026",
    )

    assert calls == [(13, "IDX_I", "2026-10-08")]
    assert result.provider_symbol == "Dhan:NIFTY"
    assert result.chain.loc[0, "strike"] == 25100.0


def test_nse_v3_fetch_uses_current_expiry_endpoint(monkeypatch):
    calls = []

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "records": {
                    "underlyingValue": 25100.0,
                    "data": [
                        {
                            "strikePrice": 25000,
                            "expiryDate": "08-Oct-2026",
                            "CE": {"lastPrice": 150.0, "openInterest": 1000},
                            "PE": {"lastPrice": 100.0, "openInterest": 1200},
                        }
                    ],
                }
            }

    class FakeSession:
        def get(self, url, **kwargs):
            calls.append((url, kwargs))
            return FakeResponse()

    monkeypatch.setattr(
        "services.options_analytics._fetch_nse_expiries",
        lambda underlying: ("08-Oct-2026", "15-Oct-2026"),
    )
    monkeypatch.setattr(
        "services.options_analytics._nse_session",
        lambda: FakeSession(),
    )

    from services.options_analytics import _fetch_nse_option_chain

    payload = _fetch_nse_option_chain("NIFTY", "08-Oct-2026")

    assert calls[0][0].endswith("/api/option-chain-v3")
    assert calls[0][1]["params"] == {
        "type": "Indices",
        "symbol": "NIFTY",
        "expiry": "08-Oct-2026",
    }
    assert payload["records"]["expiryDates"] == ["08-Oct-2026", "15-Oct-2026"]


def test_nse_v3_can_discover_expiry_when_contract_info_fails(monkeypatch):
    calls = []

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "records": {
                    "underlyingValue": 25100.0,
                    "expiryDates": ["08-Oct-2026", "15-Oct-2026"],
                    "data": [
                        {
                            "strikePrice": 25000,
                            "expiryDate": "08-Oct-2026",
                            "CE": {"lastPrice": 150.0, "openInterest": 1000},
                            "PE": {"lastPrice": 100.0, "openInterest": 1200},
                        }
                    ],
                }
            }

    class FakeSession:
        def get(self, url, **kwargs):
            calls.append((url, kwargs))
            return FakeResponse()

    def fail_contract_info(underlying):
        raise RuntimeError("contract-info unavailable")

    monkeypatch.setattr(
        "services.options_analytics._fetch_nse_expiries",
        fail_contract_info,
    )
    monkeypatch.setattr(
        "services.options_analytics._nse_session",
        lambda: FakeSession(),
    )

    from services.options_analytics import _fetch_nse_option_chain

    payload = _fetch_nse_option_chain("NIFTY")

    assert calls[0][0].endswith("/api/option-chain-v3")
    assert calls[0][1]["params"] == {
        "type": "Indices",
        "symbol": "NIFTY",
    }
    assert payload["records"]["expiryDates"] == ["08-Oct-2026", "15-Oct-2026"]


def test_fetch_option_chain_explains_dhan_http_401(monkeypatch):
    from services.options_analytics import OptionChainResult

    monkeypatch.setattr(
        "services.options_analytics._fetch_dhan_option_chain",
        lambda underlying, expiry=None: (_ for _ in ()).throw(
            RuntimeError("Dhan /optionchain/expirylist HTTP 401; SDK response unavailable")
        ),
    )
    monkeypatch.setattr(
        "services.options_analytics._fetch_nse_option_chain",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("NSE unavailable")),
    )
    monkeypatch.setattr(
        "services.options_analytics._fetch_yahoo_option_chain",
        lambda underlying, expiry: OptionChainResult(
            underlying=underlying,
            provider_symbol="^NSEI",
            expiry=expiry,
            spot=None,
            chain=pd.DataFrame(),
            expiries=(),
            status="UNAVAILABLE",
            message="Yahoo option chain unavailable",
        ),
    )

    result = fetch_option_chain("NIFTY")

    assert result.status == "UNAVAILABLE"
    assert "HTTP 401 Unauthorized" in result.message
    assert "DHAN_CLIENT_ID" in result.message
    assert "DHAN_ACCESS_TOKEN" in result.message
    assert "Never paste credentials" in result.message
