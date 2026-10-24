"""Diagnose which market-data providers work from THIS machine and network.

Run it before starting the app:

    uv run python scripts/check_providers.py        (or: make doctor)

Options chains and BSE data depend on your network and credentials, which no test suite
can know. This prints PASS / WARN / FAIL per check with the next step to take. Secrets are
never printed: any credential value that appears in an error message is redacted.
"""

from __future__ import annotations

import importlib
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SECRET_ENV_VARS = ("DHAN_ACCESS_TOKEN", "DHAN_CLIENT_ID", "SUPABASE_SECRET_KEY")
PASS, WARN, FAIL = "PASS", "WARN", "FAIL"


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    detail: str


def redact(text: str, environ: dict[str, str] | None = None) -> str:
    """Replace any configured secret value found in ``text`` with ``***``."""
    values = os.environ if environ is None else environ
    for key in SECRET_ENV_VARS:
        secret = str(values.get(key, "")).strip()
        if len(secret) >= 4:
            text = text.replace(secret, "***")
    return text


def run_check(name: str, check: Callable[[], tuple[str, str]]) -> CheckResult:
    """Run one check; an exception becomes FAIL with a redacted, single-line message."""
    try:
        status, detail = check()
    except Exception as exc:  # a diagnostic must never crash on a provider error
        status, detail = FAIL, f"{type(exc).__name__}: {exc}"
    return CheckResult(name, status, redact(" ".join(str(detail).split())[:300]))


# --------------------------------------------------------------------------------------
# individual checks
# --------------------------------------------------------------------------------------
def check_python() -> tuple[str, str]:
    version = sys.version_info
    if version[:2] == (3, 13):
        return PASS, f"Python {version.major}.{version.minor}.{version.micro}"
    return WARN, f"Python {version.major}.{version.minor}; the project targets 3.13"


def check_packages() -> tuple[str, str]:
    required = ("streamlit", "pandas", "numpy", "plotly", "yfinance", "curl_cffi")
    missing = []
    for module in required:
        try:
            importlib.import_module(module)
        except ImportError:
            missing.append(module)
    if missing:
        return FAIL, f"missing {', '.join(missing)}. Run: uv sync --locked"
    try:
        importlib.import_module("dhanhq")
    except ImportError:
        return WARN, "all core packages present; 'dhanhq' missing (needed for Dhan data)"
    return PASS, "all required packages import"


def check_dhan_credentials() -> tuple[str, str]:
    from services.dhan_market_data import DhanConfigurationError, DhanCredentials

    try:
        DhanCredentials.from_env()
    except DhanConfigurationError as exc:
        return WARN, f"{exc}. Copy .env.example to .env and fill them in (options need Dhan)"
    return PASS, "DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN are set (values not shown)"


def check_dhan_options() -> tuple[str, str]:
    from services.options_analytics import _fetch_dhan_expiries

    expiries = _fetch_dhan_expiries("NIFTY")
    if not expiries:
        return FAIL, "Dhan returned no NIFTY expiries"
    return PASS, f"Dhan returned {len(expiries)} NIFTY expiries; next: {expiries[0]}"


def check_nse_options() -> tuple[str, str]:
    from services.options_analytics import _fetch_nse_expiries

    expiries = _fetch_nse_expiries("NIFTY")
    if not expiries:
        return WARN, "NSE reachable but returned no expiries"
    return PASS, f"NSE returned {len(expiries)} NIFTY expiries"


def _equity_check(ticker: str) -> tuple[str, str]:
    from services.resilient_market_data import download_market_frames

    frames, info = download_market_frames([ticker], period="1mo", interval="1d", retries=1)
    frame = frames.get(ticker)
    if frame is None or frame.empty:
        return FAIL, f"no daily data for {ticker} (missing: {info.get('missing')})"
    return (
        PASS,
        f"{len(frame)} daily bars for {ticker}, last close {float(frame['Close'].iloc[-1]):.2f}",
    )


def check_nse_equity() -> tuple[str, str]:
    return _equity_check("RELIANCE.NS")


def check_bse_equity() -> tuple[str, str]:
    return _equity_check("RELIANCE.BO")


def check_option_chain_end_to_end() -> tuple[str, str]:
    from services.options_analytics import fetch_option_chain

    result = fetch_option_chain("NIFTY")
    if result.status == "AVAILABLE":
        return (
            PASS,
            f"{result.provider_symbol}, expiry {result.expiry}, {len(result.chain)} strikes",
        )
    return FAIL, result.message


CHECKS: tuple[tuple[str, Callable[[], tuple[str, str]]], ...] = (
    ("Python version", check_python),
    ("Required packages", check_packages),
    ("Dhan credentials", check_dhan_credentials),
    ("Dhan option expiries", check_dhan_options),
    ("NSE option expiries (fallback)", check_nse_options),
    ("NSE equity data (RELIANCE.NS)", check_nse_equity),
    ("BSE equity data (RELIANCE.BO)", check_bse_equity),
    ("Option chain, end to end (NIFTY)", check_option_chain_end_to_end),
)


def summarize(results: list[CheckResult]) -> str:
    """One-line verdict for the options module and for BSE."""
    by_name = {r.name: r for r in results}
    options = by_name.get("Option chain, end to end (NIFTY)")
    bse = by_name.get("BSE equity data (RELIANCE.BO)")
    lines = []
    if options is not None:
        lines.append(
            "Options: WORKING"
            if options.status == PASS
            else "Options: NOT working here. Add Dhan credentials to .env "
            "(see .env.example); NSE/Yahoo usually block cloud and some home networks."
        )
    if bse is not None:
        lines.append(
            "BSE: WORKING"
            if bse.status == PASS
            else "BSE: NOT working here. Check your network; BSE data comes from Yahoo (.BO)."
        )
    return "\n".join(lines)


def main() -> int:
    from config.env import load_environment

    loaded = load_environment()
    print(f"Loaded .env: {'yes' if loaded else 'no (using real environment variables only)'}\n")

    results = []
    for name, check in CHECKS:
        result = run_check(name, check)
        results.append(result)
        print(f"[{result.status}] {result.name}: {result.detail}")
    print()
    print(summarize(results))
    return 1 if any(r.status == FAIL for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
