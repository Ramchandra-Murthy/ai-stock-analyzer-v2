"""NSE surveillance and liquidity safety checks for intraday candidates.

The NSE REG_IND report is used as a point-in-time reference for surveillance
indicators and trade-for-trade series. A failed refresh is treated as unknown,
not as proof that a security is clear.
"""

from __future__ import annotations

from datetime import date, timedelta
from io import StringIO

import pandas as pd
import requests

NSE_HOME = "https://www.nseindia.com"
REG_IND_URL = "https://nsearchives.nseindia.com/archives/equities/mkt/REG_IND{date}.csv"
TIMEOUT_SECONDS = 8

_FLAG_COLUMN_TERMS = (
    "SURVEILLANCE",
    "SURV_IND",
    "INDICATOR",
    "ASM",
    "GSM",
    "ESM",
)


def _normalise_symbol(value: object) -> str:
    return str(value).strip().upper().replace(".NS", "").replace(".BO", "")


def _candidate_dates(as_of: date | None = None) -> list[date]:
    current = as_of or date.today()
    return [current - timedelta(days=offset) for offset in range(0, 8)]


def _download_reg_ind(day: date, session: requests.Session) -> pd.DataFrame:
    url = REG_IND_URL.format(date=day.strftime("%d%m%y"))
    response = session.get(url, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    return pd.read_csv(StringIO(response.text))


def _flag_columns(frame: pd.DataFrame) -> list[str]:
    columns: list[str] = []
    for column in frame.columns:
        name = str(column).strip().upper().replace(" ", "_")
        if any(term in name for term in _FLAG_COLUMN_TERMS):
            columns.append(column)
    return columns


def _has_value(value: object) -> bool:
    if pd.isna(value):
        return False
    text = str(value).strip().upper()
    return text not in {"", "-", "NA", "N/A", "NAN", "NONE", "0", "0.0"}


def _classify_row(row: pd.Series, flag_columns: list[str]) -> str:
    flags: list[str] = []
    for column in flag_columns:
        value = row.get(column)
        if _has_value(value):
            flags.append(f"{column}: {str(value).strip()}")
    series = str(row.get("SERIES", "")).strip().upper()
    if series in {"BE", "BZ", "ST", "SZ"}:
        flags.append(f"Trade-to-Trade ({series})")
    return "; ".join(dict.fromkeys(flags))


def fetch_nse_safety_snapshot(
    symbols: list[str],
    as_of: date | None = None,
) -> tuple[pd.DataFrame, str | None]:
    """Return point-in-time NSE surveillance flags for requested symbols.

    The function tries recent dates so weekend/holiday scans can use the latest
    available archive. It returns an empty frame plus an error message when the
    exchange archive cannot be refreshed.
    """
    requested = {_normalise_symbol(symbol) for symbol in symbols}
    if not requested:
        return pd.DataFrame(columns=["Symbol", "Safety flags"]), "No NSE symbols."

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/153 Safari/537.36"
            ),
            "Accept": "text/csv,text/plain,*/*",
            "Referer": NSE_HOME,
        }
    )

    try:
        session.get(NSE_HOME, timeout=TIMEOUT_SECONDS)
    except requests.RequestException:
        pass

    last_error = "NSE surveillance archive unavailable."
    for day in _candidate_dates(as_of):
        try:
            frame = _download_reg_ind(day, session)
        except (requests.RequestException, ValueError, pd.errors.ParserError) as exc:
            last_error = f"NSE surveillance refresh failed: {exc}"
            continue

        symbol_column = next(
            (
                column
                for column in frame.columns
                if str(column).strip().upper() in {"SYMBOL", "SYMBOLS"}
            ),
            None,
        )
        if symbol_column is None:
            last_error = "NSE REG_IND report has no symbol column."
            continue

        flag_columns = _flag_columns(frame)
        if not flag_columns:
            last_error = "NSE REG_IND report has no surveillance indicator columns."
            continue

        frame = frame.copy()
        frame["_symbol"] = frame[symbol_column].map(_normalise_symbol)
        frame = frame[frame["_symbol"].isin(requested)]
        frame["Safety flags"] = frame.apply(
            lambda row, columns=flag_columns: _classify_row(row, columns),
            axis=1,
        )
        result = frame[["_symbol", "Safety flags"]].rename(columns={"_symbol": "Symbol"})
        result["Surveillance date"] = day.isoformat()
        result["Found in archive"] = True
        result = result.drop_duplicates("Symbol")

        requested_frame = pd.DataFrame({"Symbol": sorted(requested)})
        result = requested_frame.merge(result, on="Symbol", how="left")
        result["Safety flags"] = result["Safety flags"].fillna("")
        result["Surveillance date"] = result["Surveillance date"].fillna(day.isoformat())
        result["Found in archive"] = result["Found in archive"].fillna(False)
        result["Safety status"] = result.apply(
            lambda row: (
                "Flagged - review before trading"
                if str(row["Safety flags"]).strip()
                else "NSE check clear" if bool(row["Found in archive"]) else "NSE check unavailable"
            ),
            axis=1,
        )
        return result, None

    return pd.DataFrame(columns=["Symbol", "Safety flags"]), last_error


def apply_safety_filter(
    candidates: pd.DataFrame,
    safety: pd.DataFrame,
    exclude_flagged: bool = True,
) -> pd.DataFrame:
    """Annotate candidates and optionally remove known NSE safety flags."""
    if candidates is None or candidates.empty:
        return pd.DataFrame() if candidates is None else candidates.copy()

    result = candidates.copy()
    result["Safety flags"] = ""
    result["Safety status"] = "Manual check required"

    if safety is not None and not safety.empty:
        lookup = safety.drop_duplicates("Symbol").set_index("Symbol")
        result["Safety flags"] = result["Symbol"].map(lookup["Safety flags"]).fillna("")
        status_series = (
            lookup["Safety status"] if "Safety status" in lookup.columns else pd.Series(dtype=str)
        )
        result["Safety status"] = (
            result["Symbol"].map(status_series).fillna("Manual check required")
        )

    if exclude_flagged:
        result = result[result["Safety flags"].fillna("").eq("")].copy()

    return result.reset_index(drop=True)


def liquidity_warning(
    price: float,
    latest_volume: float,
    min_candle_value: float = 2_000_000.0,
) -> str:
    """Flag a very small latest-candle traded value as a liquidity warning."""
    if price <= 0 or latest_volume < 0:
        return "Liquidity data invalid"
    value = price * latest_volume
    return "Low recent traded value" if value < min_candle_value else "OK"
