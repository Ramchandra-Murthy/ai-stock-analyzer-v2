from services.dhan_market_data import (
    NIFTY_50_SECURITY_ID,
    NIFTY_INDEX_SEGMENT,
    DhanConfigurationError,
    DhanCredentials,
    DhanMarketData,
)


class FakeDhanClient:
    def ticker_data(self, securities):
        return {"status": "success", "data": securities}

    def ohlc_data(self, securities):
        return {"status": "success", "data": securities}

    def quote_data(self, securities):
        return {"status": "success", "data": securities}

    def expiry_list(self, security_id, segment):
        return {"status": "success", "data": [security_id, segment]}

    def option_chain(self, security_id, segment, expiry):
        return {"status": "success", "data": [security_id, segment, expiry]}


def test_dhan_credentials_load_without_exposing_values():
    credentials = DhanCredentials.from_env(
        {
            "DHAN_CLIENT_ID": "client-123",
            "DHAN_ACCESS_TOKEN": "secret-token",
        }
    )

    assert credentials.client_id == "client-123"
    assert credentials.access_token == "secret-token"


def test_dhan_credentials_reject_missing_values():
    try:
        DhanCredentials.from_env({"DHAN_CLIENT_ID": "client-123"})
    except DhanConfigurationError as exc:
        assert "DHAN_ACCESS_TOKEN" in str(exc)
    else:
        raise AssertionError("Expected missing Dhan access-token configuration to fail")


def test_dhan_market_data_uses_read_only_quote_methods():
    dhan = DhanMarketData(client=FakeDhanClient())

    assert dhan.ticker_data({"NSE_EQ": [1333]})["status"] == "success"
    assert dhan.ohlc_data({"NSE_EQ": [1333]})["status"] == "success"
    assert dhan.quote_data({"NSE_EQ": [1333]})["status"] == "success"


def test_nifty_helpers_use_dhan_index_contract():
    dhan = DhanMarketData(client=FakeDhanClient())

    assert dhan.nifty_ltp()["data"] == {NIFTY_INDEX_SEGMENT: [NIFTY_50_SECURITY_ID]}
    assert dhan.nifty_expiries()["data"] == [NIFTY_50_SECURITY_ID, NIFTY_INDEX_SEGMENT]
    assert dhan.nifty_option_chain("2026-10-13")["data"] == [
        NIFTY_50_SECURITY_ID,
        NIFTY_INDEX_SEGMENT,
        "2026-10-13",
    ]


class FailingOptionClient(FakeDhanClient):
    def expiry_list(self, security_id, segment):
        return {
            "status": "failure",
            "remarks": {
                "error_code": None,
                "error_type": None,
                "error_message": None,
            },
        }

    def option_chain(self, security_id, segment, expiry):
        return {
            "status": "failure",
            "remarks": {
                "error_code": None,
                "error_type": None,
                "error_message": None,
            },
        }


class FakeHttpResponse:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        import json

        return json.dumps(self._payload).encode("utf-8")


def test_option_apis_retry_with_direct_dhan_rest(monkeypatch):
    import services.dhan_market_data as module

    calls = []

    def fake_urlopen(request, timeout):
        headers = {key.lower(): value for key, value in request.header_items()}
        calls.append((request.full_url, headers.get("client-id"), timeout))
        if request.full_url.endswith("/expirylist"):
            raise AssertionError("unexpected URL")
        return FakeHttpResponse({"status": "success", "data": {"last_price": 25000, "oc": {}}})

    def fake_option_urlopen(request, timeout):
        headers = {key.lower(): value for key, value in request.header_items()}
        calls.append((request.full_url, headers.get("client-id"), timeout))
        return FakeHttpResponse({"status": "success", "data": ["direct"]})

    monkeypatch.setattr(module, "urlopen", fake_option_urlopen)
    credentials = DhanCredentials("client-123", "secret-token")
    dhan = DhanMarketData(credentials=credentials, client=FailingOptionClient())

    response = dhan.option_chain(13, "IDX_I", "2026-10-08")

    assert response["status"] == "success"
    assert calls == [("https://api.dhan.co/v2/optionchain", "client-123", 15)]


def test_dhan_credentials_load_from_streamlit_secrets_when_environment_is_missing(monkeypatch):
    import sys
    from types import SimpleNamespace

    monkeypatch.setitem(
        sys.modules,
        "streamlit",
        SimpleNamespace(
            secrets={
                "DHAN_CLIENT_ID": "streamlit-client",
                "DHAN_ACCESS_TOKEN": "streamlit-token",
            }
        ),
    )

    credentials = DhanCredentials.from_env({})

    assert credentials.client_id == "streamlit-client"
    assert credentials.access_token == "streamlit-token"


def test_dhan_environment_credentials_take_precedence_over_streamlit_secrets(monkeypatch):
    import sys
    from types import SimpleNamespace

    monkeypatch.setitem(
        sys.modules,
        "streamlit",
        SimpleNamespace(
            secrets={
                "DHAN_CLIENT_ID": "streamlit-client",
                "DHAN_ACCESS_TOKEN": "streamlit-token",
            }
        ),
    )

    credentials = DhanCredentials.from_env(
        {
            "DHAN_CLIENT_ID": "environment-client",
            "DHAN_ACCESS_TOKEN": "environment-token",
        }
    )

    assert credentials.client_id == "environment-client"
    assert credentials.access_token == "environment-token"


def test_dhan_network_error_does_not_expose_exception_text(monkeypatch):
    from urllib.error import URLError

    import services.dhan_market_data as module

    secret_marker = "secret-token-must-not-appear"

    def fail_urlopen(_request, timeout):
        raise URLError(f"failed URL includes {secret_marker}")

    monkeypatch.setattr(module, "urlopen", fail_urlopen)
    credentials = DhanCredentials("client-123", secret_marker)
    dhan = DhanMarketData(credentials=credentials, client=FailingOptionClient())

    try:
        dhan.option_chain(13, "IDX_I", "2026-10-08")
    except DhanConfigurationError as exc:
        assert "URLError" in str(exc)
        assert secret_marker not in str(exc)
    else:
        raise AssertionError("Expected the Dhan direct request to fail")


def test_dhan_http_401_has_safe_token_remediation(monkeypatch):
    from urllib.error import HTTPError

    import services.dhan_market_data as module

    def unauthorized(_request, timeout):
        raise HTTPError(
            "https://api.dhan.co/v2/optionchain",
            401,
            "Unauthorized",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(module, "urlopen", unauthorized)
    dhan = DhanMarketData(
        credentials=DhanCredentials("client-123", "secret-token"),
        client=FailingOptionClient(),
    )

    try:
        dhan.option_chain(13, "IDX_I", "2026-10-08")
    except DhanConfigurationError as exc:
        message = str(exc)
        assert "HTTP 401" in message
        assert "DHAN_CLIENT_ID" in message
        assert "DHAN_ACCESS_TOKEN" in message
        assert "fresh access token" in message
        assert "secret-token" not in message
    else:
        raise AssertionError("Expected Dhan HTTP 401 to fail")
