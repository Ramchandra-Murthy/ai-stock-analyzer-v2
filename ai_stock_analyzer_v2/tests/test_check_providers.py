"""Tests for the provider diagnostic: it must never crash and never leak credentials."""

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check_providers.py"
spec = importlib.util.spec_from_file_location("check_providers", SCRIPT)
check_providers = importlib.util.module_from_spec(spec)
sys.modules["check_providers"] = check_providers  # dataclasses look the module up here
spec.loader.exec_module(check_providers)


def test_redact_removes_configured_secrets() -> None:
    env = {"DHAN_ACCESS_TOKEN": "tok-ABC123456", "DHAN_CLIENT_ID": "1100998877"}

    text = check_providers.redact("HTTP 401 for tok-ABC123456 client 1100998877", env)

    assert "tok-ABC123456" not in text and "1100998877" not in text
    assert text.count("***") == 2


def test_redact_ignores_blank_and_tiny_values() -> None:
    env = {"DHAN_ACCESS_TOKEN": "", "DHAN_CLIENT_ID": "ab"}

    assert check_providers.redact("about ab", env) == "about ab"


def test_exception_becomes_fail_and_secret_is_redacted(monkeypatch) -> None:
    monkeypatch.setenv("DHAN_ACCESS_TOKEN", "super-secret-token-value")

    def boom() -> tuple[str, str]:
        raise RuntimeError("request failed with token super-secret-token-value\nline two")

    result = check_providers.run_check("x", boom)

    assert result.status == check_providers.FAIL
    assert "super-secret-token-value" not in result.detail
    assert "\n" not in result.detail


def test_passing_check_is_reported_as_returned() -> None:
    result = check_providers.run_check("x", lambda: (check_providers.PASS, "fine"))

    assert (result.status, result.detail) == (check_providers.PASS, "fine")


def test_summary_tells_user_whether_options_and_bse_work() -> None:
    P, F = check_providers.PASS, check_providers.FAIL
    results = [
        check_providers.CheckResult("Option chain, end to end (NIFTY)", F, "blocked"),
        check_providers.CheckResult("BSE equity data (RELIANCE.BO)", P, "ok"),
    ]

    summary = check_providers.summarize(results)

    assert "Options: NOT working" in summary and ".env" in summary
    assert "BSE: WORKING" in summary


def test_every_registered_check_is_callable_and_named() -> None:
    assert len(check_providers.CHECKS) >= 6
    for name, check in check_providers.CHECKS:
        assert name and callable(check)
