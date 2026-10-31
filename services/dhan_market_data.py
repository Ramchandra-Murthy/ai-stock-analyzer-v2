"""Read-only DhanHQ market-data adapter.

The adapter deliberately excludes order-management APIs. Credentials are loaded
from the environment and are never logged or persisted by this module.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

NIFTY_50_SECURITY_ID = 13
NIFTY_INDEX_SEGMENT = "IDX_I"


class DhanConfigurationError(RuntimeError):
    """Raised when Dhan market-data configuration is incomplete."""


@dataclass(frozen=True)
class DhanCredentials:
    """Dhan credentials required to construct the official Python client."""

    client_id: str
    access_token: str

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> DhanCredentials:
        """Load credentials from environment variables or Streamlit secrets.

        Explicit environment values take precedence. Streamlit secrets are
        consulted only for values missing from the environment, and secrets
        are never copied into logs or error messages.
        """
        values = os.environ if environ is None else environ
        client_id = str(values.get("DHAN_CLIENT_ID", "")).strip()
        access_token = str(values.get("DHAN_ACCESS_TOKEN", "")).strip()

        if not client_id or not access_token:
            try:
                import streamlit as st

                secrets = st.secrets
                if not client_id:
                    client_id = str(secrets.get("DHAN_CLIENT_ID", "")).strip()
                if not access_token:
                    access_token = str(secrets.get("DHAN_ACCESS_TOKEN", "")).strip()
            except Exception as exc:
                logger.debug("Streamlit secrets unavailable: %s", exc)
                # Streamlit may be absent or secrets may be unavailable in CLI/tests.

        missing = [
            name
            for name, value in (
                ("DHAN_CLIENT_ID", client_id),
                ("DHAN_ACCESS_TOKEN", access_token),
            )
            if not value
        ]
        if missing:
            raise DhanConfigurationError(
                f"Missing required Dhan configuration: {', '.join(missing)}"
            )
        return cls(client_id=client_id, access_token=access_token)


def _build_dhan_client(credentials: DhanCredentials) -> Any:
    """Construct the official DhanHQ Python client lazily."""
    try:
        from dhanhq import DhanContext, dhanhq
    except ImportError as exc:
        raise DhanConfigurationError(
            "The optional DhanHQ Python client is not installed. "
            "Install the official 'dhanhq' package before enabling Dhan data."
        ) from exc

    return dhanhq(DhanContext(credentials.client_id, credentials.access_token))


DHAN_API_BASE_URL = "https://api.dhan.co/v2"


def _response_remarks(response: Any) -> str:
    """Format Dhan failure details without leaking credentials."""
    if not isinstance(response, dict):
        return str(response)
    remarks = response.get("remarks")
    if remarks in (None, "", {}):
        error_code = response.get("error_code")
        error_type = response.get("error_type")
        error_message = response.get("error_message")
        details = [value for value in (error_code, error_type, error_message) if value]
        return ", ".join(str(value) for value in details) or "Dhan returned no failure details."
    return str(remarks)


class DhanMarketData:
    """Read-only wrapper around DhanHQ market-data APIs."""

    def __init__(
        self,
        *,
        credentials: DhanCredentials | None = None,
        client: Any | None = None,
    ) -> None:
        if client is not None:
            self._credentials = credentials
            self._client = client
            return
        self._credentials = credentials if credentials is not None else DhanCredentials.from_env()
        self._client = _build_dhan_client(self._credentials)

    def ticker_data(self, securities: Mapping[str, list[int]]) -> dict[str, Any]:
        """Return LTP data for the requested Dhan security IDs."""
        return self._client.ticker_data(dict(securities))

    def ohlc_data(self, securities: Mapping[str, list[int]]) -> dict[str, Any]:
        """Return OHLC plus LTP data for the requested securities."""
        return self._client.ohlc_data(dict(securities))

    def quote_data(self, securities: Mapping[str, list[int]]) -> dict[str, Any]:
        """Return full quote/depth/OI/volume data for the requested securities."""
        return self._client.quote_data(dict(securities))

    def expiry_list(
        self,
        under_security_id: int,
        under_exchange_segment: str,
    ) -> dict[str, Any]:
        """Return active option expiries, with a raw REST fallback for SDK failures."""
        response = self._client.expiry_list(
            under_security_id,
            under_exchange_segment,
        )
        if isinstance(response, dict) and response.get("status") == "success":
            return response
        return self._direct_option_api(
            "/optionchain/expirylist",
            {
                "UnderlyingScrip": under_security_id,
                "UnderlyingSeg": under_exchange_segment,
            },
            response,
        )

    def option_chain(
        self,
        under_security_id: int,
        under_exchange_segment: str,
        expiry: str,
    ) -> dict[str, Any]:
        """Return an option chain, with a raw REST fallback for SDK failures."""
        response = self._client.option_chain(
            under_security_id,
            under_exchange_segment,
            expiry,
        )
        if isinstance(response, dict) and response.get("status") == "success":
            return response
        return self._direct_option_api(
            "/optionchain",
            {
                "UnderlyingScrip": under_security_id,
                "UnderlyingSeg": under_exchange_segment,
                "Expiry": expiry,
            },
            response,
        )

    def _direct_option_api(
        self,
        endpoint: str,
        payload: dict[str, Any],
        sdk_response: Any,
    ) -> dict[str, Any]:
        """Retry option APIs directly when the SDK cannot decode a response."""
        credentials = self._credentials
        if credentials is None:
            raise DhanConfigurationError(
                "Dhan credentials are required for the direct option API fallback."
            )
        request = Request(
            f"{DHAN_API_BASE_URL}{endpoint}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "client-id": credentials.client_id,
                "access-token": credentials.access_token,
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=15) as response:
                raw = response.read().decode("utf-8")
            parsed = json.loads(raw)
        except HTTPError as exc:
            remediation = ""
            if exc.code in (401, 403):
                remediation = (
                    " Verify DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN in deployment secrets; "
                    "generate a fresh access token if expired, update the secret, "
                    "and restart the app."
                )
            raise DhanConfigurationError(
                f"Dhan {endpoint} HTTP {exc.code}.{remediation} SDK response: "
                f"{_response_remarks(sdk_response)}"
            ) from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            failure_kind = type(exc).__name__
            raise DhanConfigurationError(
                f"Dhan {endpoint} direct request failed ({failure_kind}); "
                f"SDK response: {_response_remarks(sdk_response)}"
            ) from exc
        if not isinstance(parsed, dict):
            raise DhanConfigurationError(
                f"Dhan {endpoint} returned an invalid response; "
                f"SDK response: {_response_remarks(sdk_response)}"
            )
        if parsed.get("status") != "success":
            raise DhanConfigurationError(
                f"Dhan {endpoint} failed: {_response_remarks(parsed)}; "
                f"SDK response: {_response_remarks(sdk_response)}"
            )
        return parsed

    def intraday_minute_data(
        self,
        security_id: int | str,
        exchange_segment: str,
        instrument_type: str,
        from_date: str,
        to_date: str,
        interval: int = 1,
    ) -> dict[str, Any]:
        """Return read-only intraday OHLCV candles from Dhan."""
        return self._client.intraday_minute_data(
            security_id,
            exchange_segment,
            instrument_type,
            from_date,
            to_date,
            interval=interval,
            oi=False,
        )

    def nifty_ltp(self) -> dict[str, Any]:
        """Return the NIFTY 50 LTP response using Dhan's index instrument."""
        return self.ticker_data({NIFTY_INDEX_SEGMENT: [NIFTY_50_SECURITY_ID]})

    def nifty_expiries(self) -> dict[str, Any]:
        """Return active NIFTY 50 option expiries."""
        return self.expiry_list(NIFTY_50_SECURITY_ID, NIFTY_INDEX_SEGMENT)

    def nifty_option_chain(self, expiry: str) -> dict[str, Any]:
        """Return the NIFTY 50 option chain for a specific expiry."""
        return self.option_chain(
            NIFTY_50_SECURITY_ID,
            NIFTY_INDEX_SEGMENT,
            expiry,
        )
