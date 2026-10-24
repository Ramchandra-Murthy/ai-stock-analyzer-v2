"""Alerts via Telegram and e-mail, with rules, cooldown and secret redaction.

Secrets are read only from environment variables (never from code or arguments echoed to
logs): TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
ALERT_EMAIL_TO. Transports are injectable so everything is testable without a network.
"""

from __future__ import annotations

import os
import smtplib
import time
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from email.message import EmailMessage

SECRET_ENV = ("TELEGRAM_BOT_TOKEN", "SMTP_PASSWORD")


@dataclass(frozen=True)
class Alert:
    key: str  # dedupe key, e.g. "drawdown:RELIANCE"
    title: str
    body: str


def redact(text: str, env: Mapping[str, str] | None = None) -> str:
    """Replace any configured secret value found in ``text``."""
    source = os.environ if env is None else env
    for name in SECRET_ENV:
        value = source.get(name)
        if value:
            text = text.replace(value, "***")
    return text


def telegram_configured(env: Mapping[str, str] | None = None) -> bool:
    source = os.environ if env is None else env
    return bool(source.get("TELEGRAM_BOT_TOKEN") and source.get("TELEGRAM_CHAT_ID"))


def email_configured(env: Mapping[str, str] | None = None) -> bool:
    source = os.environ if env is None else env
    return all(source.get(k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "ALERT_EMAIL_TO"))


def _http_post(url: str, data: bytes) -> int:
    request = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310 - fixed https host
        return int(response.status)


def send_telegram(
    alert: Alert,
    env: Mapping[str, str] | None = None,
    post: Callable[[str, bytes], int] = _http_post,
) -> None:
    source = os.environ if env is None else env
    if not telegram_configured(source):
        raise RuntimeError("Telegram is not configured (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID).")
    url = f"https://api.telegram.org/bot{source['TELEGRAM_BOT_TOKEN']}/sendMessage"
    data = urllib.parse.urlencode(
        {"chat_id": source["TELEGRAM_CHAT_ID"], "text": f"{alert.title}\n{alert.body}"}
    ).encode()
    try:
        status = post(url, data)
    except Exception as exc:  # never leak the token via the URL in an error message
        raise RuntimeError(redact(f"Telegram send failed: {exc}", source)) from None
    if status != 200:
        raise RuntimeError(f"Telegram send failed with HTTP {status}")


def send_email(
    alert: Alert,
    env: Mapping[str, str] | None = None,
    smtp_factory: Callable[..., object] | None = None,
) -> None:
    source = os.environ if env is None else env
    if not email_configured(source):
        raise RuntimeError(
            "E-mail is not configured (SMTP_HOST, SMTP_USER, SMTP_PASSWORD, ALERT_EMAIL_TO)."
        )
    message = EmailMessage()
    message["Subject"] = alert.title
    message["From"] = source["SMTP_USER"]
    message["To"] = source["ALERT_EMAIL_TO"]
    message.set_content(alert.body)
    factory = smtp_factory or smtplib.SMTP
    try:
        with factory(source["SMTP_HOST"], int(source.get("SMTP_PORT", "587")), timeout=15) as smtp:  # type: ignore[operator]
            smtp.starttls()  # type: ignore[attr-defined]
            smtp.login(source["SMTP_USER"], source["SMTP_PASSWORD"])  # type: ignore[attr-defined]
            smtp.send_message(message)  # type: ignore[attr-defined]
    except Exception as exc:
        raise RuntimeError(redact(f"E-mail send failed: {exc}", source)) from None


@dataclass
class AlertDispatcher:
    """Send each alert at most once per ``cooldown`` seconds per key."""

    senders: list[Callable[[Alert], None]]
    cooldown: float = 6 * 3600.0
    clock: Callable[[], float] = time.time
    _last: dict[str, float] = field(default_factory=dict)

    def dispatch(self, alerts: list[Alert]) -> tuple[int, list[str]]:
        sent, errors = 0, []
        now = self.clock()
        for alert in alerts:
            last = self._last.get(alert.key)
            if last is not None and now - last < self.cooldown:
                continue
            delivered = False
            for sender in self.senders:
                try:
                    sender(alert)
                    delivered = True
                except Exception as exc:
                    errors.append(redact(str(exc)))
            if delivered:  # only suppress repeats once something actually went out
                self._last[alert.key] = now
                sent += 1
        return sent, errors


def drawdown_rule(name: str, drawdown: float, limit: float) -> Alert | None:
    """Alert when drawdown (negative number) is at or beyond -limit."""
    if limit <= 0:
        raise ValueError("limit must be positive")
    if drawdown <= -limit:
        return Alert(
            f"drawdown:{name}",
            f"Drawdown alert: {name}",
            f"{name} drawdown is {drawdown:.1%}, beyond the {limit:.0%} limit.",
        )
    return None


def signal_change_rule(name: str, previous: float, current: float) -> Alert | None:
    if previous == current:
        return None
    label = {1.0: "LONG", 0.0: "FLAT", -1.0: "SHORT"}
    return Alert(
        f"signal:{name}:{current}",
        f"Signal change: {name}",
        f"{name} moved {label.get(previous, previous)} -> {label.get(current, current)}.",
    )


def configured_senders(env: Mapping[str, str] | None = None) -> list[Callable[[Alert], None]]:
    senders: list[Callable[[Alert], None]] = []
    if telegram_configured(env):
        senders.append(lambda a: send_telegram(a, env))
    if email_configured(env):
        senders.append(lambda a: send_email(a, env))
    return senders


__all__ = [
    "Alert",
    "AlertDispatcher",
    "configured_senders",
    "drawdown_rule",
    "redact",
    "send_email",
    "send_telegram",
    "signal_change_rule",
]
