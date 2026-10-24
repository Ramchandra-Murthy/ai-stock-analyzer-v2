import pandas as pd

from services.resilient_market_data import download_symbol_frames

_REQUIRED_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


def download_stock(symbol, period="1y", interval="1d"):
    """Download one stock's OHLCV history with bounded retries and recovery.

    Explicit Yahoo Finance suffixes are preserved so both NSE (.NS) and BSE
    (.BO) symbols work. Unsuffixed symbols retain the app's NSE default.
    An unavailable quote returns an empty frame with a stable OHLCV schema.
    """
    ticker = str(symbol).strip().upper()
    if not ticker:
        return pd.DataFrame(columns=_REQUIRED_COLUMNS)
    if "." not in ticker:
        ticker += ".NS"

    try:
        frames, _missing = download_symbol_frames(
            [ticker],
            period=period,
            interval=interval,
            auto_adjust=True,
            batch_size=1,
            recover_missing=True,
        )
        df = frames.get(ticker)
        if df is None or df.empty:
            return pd.DataFrame(columns=_REQUIRED_COLUMNS)
        df = df.copy()
    except Exception:
        return pd.DataFrame(columns=_REQUIRED_COLUMNS)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if not set(_REQUIRED_COLUMNS).issubset(df.columns):
        return pd.DataFrame(columns=_REQUIRED_COLUMNS)

    df = df[_REQUIRED_COLUMNS].copy()
    df = df.dropna(subset=_REQUIRED_COLUMNS)
    return df
