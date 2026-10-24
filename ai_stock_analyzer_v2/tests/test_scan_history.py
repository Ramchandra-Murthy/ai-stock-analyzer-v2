"""Tests for EROS scan-history persistence."""

from api.scan_history import recent_scans, save_completed_scan


def test_scan_history_round_trip(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "eros.sqlite3"
    monkeypatch.setenv("EROS_SCAN_DB", str(db_path))

    save_completed_scan(
        "job-1",
        "2026-09-24T10:00:00+00:00",
        [{"Symbol": "TEST", "Change over 5m": 1.5}],
        {"candidate_count": 1},
    )

    scans = recent_scans(1)

    assert scans[0]["job_id"] == "job-1"
    assert scans[0]["count"] == 1
    assert scans[0]["results"][0]["Symbol"] == "TEST"
    assert scans[0]["scan_stats"]["candidate_count"] == 1
