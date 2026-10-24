import pytest

from services import alerts as al

ENV = {
    "TELEGRAM_BOT_TOKEN": "123:SECRETTOKEN",
    "TELEGRAM_CHAT_ID": "42",
    "SMTP_HOST": "h",
    "SMTP_USER": "me@x.com",
    "SMTP_PASSWORD": "pw-secret",
    "ALERT_EMAIL_TO": "you@x.com",
}
A = al.Alert("k", "T", "B")


def test_redact_hides_secrets():
    assert al.redact("url /bot123:SECRETTOKEN/x pw-secret", ENV) == "url /bot***/x ***"


def test_telegram_builds_request_and_never_leaks_token_on_error():
    seen = {}

    def ok(url, data):
        seen["url"], seen["data"] = url, data
        return 200

    al.send_telegram(A, ENV, post=ok)
    assert seen["url"].endswith("/sendMessage") and b"chat_id=42" in seen["data"]

    def boom(url, data):
        raise OSError(f"failed {url}")

    with pytest.raises(RuntimeError) as exc:
        al.send_telegram(A, ENV, post=boom)
    assert "SECRETTOKEN" not in str(exc.value)
    with pytest.raises(RuntimeError, match="HTTP 500"):
        al.send_telegram(A, ENV, post=lambda u, d: 500)
    with pytest.raises(RuntimeError, match="not configured"):
        al.send_telegram(A, {})


def test_email_uses_starttls_login_and_sends():
    log = []

    class Smtp:
        def __init__(self, host, port, timeout):
            log.append(("init", host, port))

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def starttls(self):
            log.append("tls")

        def login(self, u, p):
            log.append(("login", u))

        def send_message(self, m):
            log.append(("send", m["Subject"], m["To"]))

    al.send_email(A, ENV, smtp_factory=Smtp)
    assert log == [("init", "h", 587), "tls", ("login", "me@x.com"), ("send", "T", "you@x.com")]
    with pytest.raises(RuntimeError, match="not configured"):
        al.send_email(A, {})


def test_email_error_is_redacted():
    class Bad:
        def __init__(self, *a, **k):
            raise OSError("auth pw-secret rejected")

    with pytest.raises(RuntimeError) as exc:
        al.send_email(A, ENV, smtp_factory=Bad)
    assert "pw-secret" not in str(exc.value)


def test_cooldown_dedupes_per_key_and_expires():
    sent, now = [], [0.0]
    d = al.AlertDispatcher([sent.append], cooldown=100, clock=lambda: now[0])
    assert d.dispatch([al.Alert("a", "t", "b"), al.Alert("b", "t", "b")])[0] == 2
    now[0] = 50
    assert d.dispatch([al.Alert("a", "t", "b")])[0] == 0
    now[0] = 150
    assert d.dispatch([al.Alert("a", "t", "b")])[0] == 1
    assert len(sent) == 3


def test_failed_delivery_is_retried_not_suppressed():
    calls = []

    def flaky(alert):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("down")

    d = al.AlertDispatcher([flaky], cooldown=1000, clock=lambda: 0.0)
    assert d.dispatch([A]) == (0, ["down"])
    assert d.dispatch([A])[0] == 1


def test_rules():
    assert al.drawdown_rule("X", -0.05, 0.10) is None
    assert al.drawdown_rule("X", -0.12, 0.10).key == "drawdown:X"
    with pytest.raises(ValueError):
        al.drawdown_rule("X", -0.1, 0)
    assert al.signal_change_rule("X", 1.0, 1.0) is None
    assert "LONG -> FLAT" in al.signal_change_rule("X", 1.0, 0.0).body


def test_configured_senders_follow_env():
    assert al.configured_senders({}) == []
    assert len(al.configured_senders(ENV)) == 2
