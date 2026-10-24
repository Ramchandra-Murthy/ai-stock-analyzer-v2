"""Check watched NSE symbols and send alerts (run from cron or a scheduler).

Environment: ALERT_SYMBOLS="RELIANCE,TCS" ALERT_STRATEGY="Supertrend" ALERT_DRAWDOWN=0.10
plus the Telegram/SMTP variables described in services/alerts.py. Previous signals are kept
in a small JSON file (ALERT_STATE, default data/alert_state.json). Analysis only.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from algorithmic_trading.risk_metrics import drawdown_series  # noqa: E402
from algorithmic_trading.strategy_lab import build_signals, normalise_price_frame  # noqa: E402
from config.env import load_environment as load_env  # noqa: E402
from services.alerts import (  # noqa: E402
    Alert,
    AlertDispatcher,
    configured_senders,
    drawdown_rule,
    signal_change_rule,
)
from services.cached_download import cached_download  # noqa: E402


def collect_alerts(
    symbols: list[str], strategy: str, limit: float, state: dict[str, float]
) -> list[Alert]:
    alerts: list[Alert] = []
    for symbol in symbols:
        raw = cached_download(f"{symbol}.NS", period="2y", auto_adjust=True, progress=False)
        try:
            frame = normalise_price_frame(raw)
        except ValueError as exc:
            print(f"{symbol}: skipped ({exc})")
            continue
        signal = float(build_signals(frame, strategy).iloc[-1])
        previous = state.get(symbol)
        if previous is not None and (a := signal_change_rule(symbol, previous, signal)):
            alerts.append(a)
        state[symbol] = signal
        dd = float(drawdown_series(frame["Close"].pct_change()).iloc[-1])
        if a := drawdown_rule(symbol, dd, limit):
            alerts.append(a)
    return alerts


def main() -> int:
    load_env()
    symbols = [
        s.strip().upper() for s in os.environ.get("ALERT_SYMBOLS", "").split(",") if s.strip()
    ]
    if not symbols:
        print("Set ALERT_SYMBOLS (comma separated NSE symbols).")
        return 2
    senders = configured_senders()
    if not senders:
        print("No alert channel configured (Telegram or SMTP variables).")
        return 2
    path = Path(os.environ.get("ALERT_STATE", "data/alert_state.json"))
    state = json.loads(path.read_text()) if path.exists() else {}
    alerts = collect_alerts(
        symbols,
        os.environ.get("ALERT_STRATEGY", "Supertrend"),
        float(os.environ.get("ALERT_DRAWDOWN", "0.10")),
        state,
    )
    sent, errors = AlertDispatcher(senders, cooldown=0.0).dispatch(alerts)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state))
    print(f"{len(alerts)} alert(s) found, {sent} sent, {len(errors)} error(s).")
    for error in errors:
        print("  ", error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
