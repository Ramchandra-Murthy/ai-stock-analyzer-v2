"""Tests for the EROS FastAPI scan manager."""

import time
from threading import Event
from unittest.mock import patch

import pandas as pd
import pytest

from api.scan_manager import ErosScanManager


def test_background_price_jump_scan_completes() -> None:
    frame = pd.DataFrame({"Symbol": ["TEST"], "Change over 5m": [1.5]})
    frame.attrs["scan_stats"] = {"candidate_count": 1}

    manager = ErosScanManager(max_workers=1)
    with patch("api.scan_manager.scan_price_jumps", return_value=frame):
        job_id = manager.start_price_jump_scan(limit=1)

        for _ in range(100):
            job = manager.get_job(job_id)
            if job and job["status"] == "completed":
                break
            time.sleep(0.01)

        assert job is not None
        assert job["status"] == "completed"
        assert job["count"] == 1
        assert job["scan_stats"]["candidate_count"] == 1
        assert job["results"][0]["Symbol"] == "TEST"


@pytest.mark.parametrize(
    ("second_lookback", "same_job"),
    [(5, True), (10, False)],
)
def test_active_price_jump_scan_parameter_handling(
    second_lookback: int,
    same_job: bool,
) -> None:
    frame = pd.DataFrame({"Symbol": ["TEST"]})
    started = Event()
    release = Event()

    def scan(**_kwargs: object) -> pd.DataFrame:
        started.set()
        release.wait(timeout=5)
        return frame

    manager = ErosScanManager(max_workers=1)
    with patch("api.scan_manager.scan_price_jumps", side_effect=scan):
        first_job_id = manager.start_price_jump_scan(
            exchange_category="NSE",
            lookback_minutes=5,
            jump_percent=1,
        )
        assert started.wait(timeout=2)

        second_job_id = manager.start_price_jump_scan(
            exchange_category="NSE",
            lookback_minutes=second_lookback,
            jump_percent=1,
        )

        if same_job:
            assert second_job_id == first_job_id
        else:
            assert second_job_id != first_job_id
        release.set()


def test_queued_price_jump_scan_keeps_matching_job() -> None:
    frame = pd.DataFrame({"Symbol": ["TEST"]})
    started = Event()
    release = Event()
    calls = 0

    def scan(**_kwargs: object) -> pd.DataFrame:
        nonlocal calls
        calls += 1
        if calls == 1:
            started.set()
            release.wait(timeout=5)
        return frame

    manager = ErosScanManager(max_workers=1)
    with patch("api.scan_manager.scan_price_jumps", side_effect=scan):
        first_job_id = manager.start_price_jump_scan(
            exchange_category="NSE",
            lookback_minutes=5,
            jump_percent=1,
        )
        assert started.wait(timeout=2)

        second_job_id = manager.start_price_jump_scan(
            exchange_category="NSE",
            lookback_minutes=10,
            jump_percent=1,
        )
        third_job_id = manager.start_price_jump_scan(
            exchange_category="NSE",
            lookback_minutes=10,
            jump_percent=1,
        )

        assert second_job_id != first_job_id
        assert third_job_id == second_job_id
        assert manager.get_job(second_job_id)["status"] == "queued"

        release.set()

        for _ in range(500):
            job = manager.get_job(second_job_id)
            if job and job["status"] == "completed":
                break
            time.sleep(0.01)

        assert job is not None
        assert job["status"] == "completed"


def test_background_day_trader_scan_completes_and_preserves_scan_stats() -> None:
    frame = pd.DataFrame({"Symbol": ["TEST"], "Opportunity score": [75.0]})
    frame.attrs["scan_stats"] = {"candidate_count": 12, "usable_data_count": 1}
    manager = ErosScanManager(max_workers=1)
    with patch("api.scan_manager.scan_day_trader_opportunities", return_value=frame):
        job_id = manager.start_day_trader_scan(exchange_category="NSE", limit=100)
        for _ in range(100):
            job = manager.get_job(job_id)
            if job and job["status"] == "completed":
                break
            time.sleep(0.01)

    assert job is not None
    assert job["status"] == "completed"
    assert job["count"] == 1
    assert job["results"][0]["Symbol"] == "TEST"
    assert job["scan_stats"] == {"candidate_count": 12, "usable_data_count": 1}


def test_identical_active_day_trader_scans_are_deduplicated() -> None:
    frame = pd.DataFrame({"Symbol": ["TEST"]})
    started = Event()
    release = Event()

    def scan(**_kwargs: object) -> pd.DataFrame:
        started.set()
        release.wait(timeout=5)
        return frame

    manager = ErosScanManager(max_workers=1)
    with patch("api.scan_manager.scan_day_trader_opportunities", side_effect=scan):
        first = manager.start_day_trader_scan(exchange_category="NSE", limit=100)
        assert started.wait(timeout=2)
        duplicate = manager.start_day_trader_scan(exchange_category="NSE", limit=100)
        different = manager.start_day_trader_scan(exchange_category="BSE", limit=100)
        assert duplicate == first
        assert different == first  # changed controls must not queue a second universe scan
        release.set()


def test_day_trader_scan_failure_is_reported_without_provider_details() -> None:
    manager = ErosScanManager(max_workers=1)
    with patch(
        "api.scan_manager.scan_day_trader_opportunities",
        side_effect=RuntimeError("https://provider.invalid/?token=secret"),
    ):
        job_id = manager.start_day_trader_scan(exchange_category="NSE")
        for _ in range(100):
            job = manager.get_job(job_id)
            if job and job["status"] == "failed":
                break
            time.sleep(0.01)

    assert job is not None
    assert job["status"] == "failed"
    assert job["error"] == "Day-Trader scan failed (RuntimeError)."
    assert "secret" not in job["error"]


def test_price_jump_queue_rejects_new_work_when_all_slots_are_active() -> None:
    started = Event()
    release = Event()

    def scan(**_kwargs: object) -> pd.DataFrame:
        started.set()
        release.wait(timeout=5)
        return pd.DataFrame()

    manager = ErosScanManager(max_workers=1, max_jobs=1)
    with patch("api.scan_manager.scan_price_jumps", side_effect=scan):
        job_id = manager.start_price_jump_scan(lookback_minutes=5)
        assert started.wait(timeout=2)

        with pytest.raises(RuntimeError, match="Scan queue is full"):
            manager.start_price_jump_scan(lookback_minutes=10)

        release.set()
        for _ in range(100):
            job = manager.get_job(job_id)
            if job and job["status"] == "completed":
                break
            time.sleep(0.01)


def test_price_jump_deduplication_does_not_match_day_trader_job() -> None:
    started = Event()
    release = Event()

    def scan(**_kwargs: object) -> pd.DataFrame:
        started.set()
        release.wait(timeout=5)
        return pd.DataFrame()

    manager = ErosScanManager(max_workers=1)
    with (
        patch("api.scan_manager.scan_day_trader_opportunities", side_effect=scan),
        patch("api.scan_manager.scan_price_jumps", return_value=pd.DataFrame()),
    ):
        day_trader_id = manager.start_day_trader_scan(exchange_category="NSE", limit=20)
        assert started.wait(timeout=2)

        price_jump_id = manager.start_price_jump_scan(exchange_category="NSE", limit=20)

        assert price_jump_id != day_trader_id
        assert manager.get_job(price_jump_id)["kind"] == "price_jump"
        release.set()
        for _ in range(100):
            job = manager.get_job(price_jump_id)
            if job and job["status"] == "completed":
                break
            time.sleep(0.01)


def test_price_jump_failure_does_not_expose_provider_error_details() -> None:
    manager = ErosScanManager(max_workers=1)
    with patch(
        "api.scan_manager.scan_price_jumps",
        side_effect=RuntimeError("https://provider.invalid/?token=secret"),
    ):
        job_id = manager.start_price_jump_scan(exchange_category="NSE")
        for _ in range(100):
            job = manager.get_job(job_id)
            if job and job["status"] == "failed":
                break
            time.sleep(0.01)

    assert job is not None
    assert job["status"] == "failed"
    assert job["error"] == "Price-jump scan failed (RuntimeError)."
    assert "secret" not in job["error"]



def test_day_trader_queue_rejects_new_work_when_all_slots_are_active() -> None:
    started = Event()
    release = Event()

    def price_jump_scan(**_kwargs: object) -> pd.DataFrame:
        started.set()
        release.wait(timeout=5)
        return pd.DataFrame()

    manager = ErosScanManager(max_workers=1, max_jobs=1)
    with (
        patch("api.scan_manager.scan_price_jumps", side_effect=price_jump_scan),
        patch("api.scan_manager.scan_day_trader_opportunities", return_value=pd.DataFrame()),
    ):
        price_job_id = manager.start_price_jump_scan(lookback_minutes=5)
        assert started.wait(timeout=2)

        with pytest.raises(RuntimeError, match="Scan queue is full"):
            manager.start_day_trader_scan(exchange_category="NSE", limit=20)

        release.set()
        for _ in range(100):
            job = manager.get_job(price_job_id)
            if job and job["status"] == "completed":
                break
            time.sleep(0.01)

