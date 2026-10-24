# Dhan market-data integration

The application now has a read-only adapter boundary for DhanHQ market data.

## Credentials

Set these environment variables outside source control:

- `DHAN_CLIENT_ID`
- `DHAN_ACCESS_TOKEN`

For Streamlit Community Cloud, the same names can be configured in the app's
**Settings → Secrets**. The adapter reads environment variables first and uses
Streamlit secrets only when a value is missing from the environment.

Never commit or log the access token. A successful configuration check does not
prove the token is valid; Dhan HTTP 401 responses must still be treated as an
authentication failure, and option-chain decisions remain blocked when provider
data is unavailable.

## Official client

The adapter uses Dhan's official `dhanhq` Python client when enabled. The
dependency is intentionally not added to the locked production dependency set
in this first boundary PR; the next integration step will add and regenerate
the lockfile before enabling Dhan in deployed scanners.

## Initial scope

The adapter supports:

- LTP/ticker data
- OHLC data
- full quote data
- option-expiry lookup
- option-chain retrieval
- NIFTY 50 convenience methods

No order-placement or order-management API is exposed by this module.


## Live Top-10 provider

The live Top-10 scanner can prefer Dhan intraday candles when both Dhan credentials and
a symbol-to-security-ID map are configured. Yahoo Finance remains the automatic fallback
for unmapped or failed Dhan symbols.

Set:

```text
DHAN_CLIENT_ID=...
DHAN_ACCESS_TOKEN=...
DHAN_SECURITY_MAP_JSON={"RELIANCE":2885,"TCS":11536}
```

The map should use the Dhan security IDs for the exchange-qualified symbols being scanned.
No order-management API is used by this provider.

The scanner requests 1-minute intraday OHLCV candles from Dhan. Dhan documents 1-minute
and 5-minute intraday candle intervals for active instruments.
