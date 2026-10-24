"""In-memory background scan manager for the EROS API."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Lock
from typing import Any
from uuid import uuid4

import pandas as pd

from api.scan_history import save_completed_scan
from scanner.price_jump import scan_price_jumps


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a DataFrame into JSON-safe records."""
    if frame is None or frame.empty:
        return []
    clean = frame.copy()
    clean = clean.astype(object).where(pd.notna(clean), None)
    return clean.to_dict(orient="records")


def _stats(frame: pd.DataFrame) -> dict[str, Any]:
    """Extract scanner diagnostics."""
    return dict(getattr(frame, "attrs", {}).get("scan_stats", {}))


class ErosScanManager:
    """Run EROS scans outside the HTTP request thread."""

    def __init__(self, max_workers: int = 1, max_jobs: int = 100) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="eros-scan",
        )
        self._jobs: dict[str, dict[str, Any]] = {}
        self._max_jobs = max(1, max_jobs)
        self._lock = Lock()
        self._active_price_jump_job: str | None = None

    def _find_matching_price_jump_job(self, kwargs: dict[str, Any]) -> str | None:
        for job_id, job in self._jobs.items():
            if job["status"] in {"queued", "running"} and job["kwargs"] == kwargs:
                return job_id
        return None

    def _next_queued_price_jump_job(self) -> str | None:
        for job_id, job in self._jobs.items():
            if job["status"] == "queued":
                return job_id
        return None

    def start_price_jump_scan(self, **kwargs: Any) -> str:
        """Queue a price-jump scan and return its job identifier."""
        job_id = uuid4().hex
        with self._lock:
            matching_job_id = self._find_matching_price_jump_job(kwargs)
            if matching_job_id is not None:
                return matching_job_id

            if len(self._jobs) >= self._max_jobs:
                terminal_job_id = next(
                    (
                        existing_id
                        for existing_id, existing_job in self._jobs.items()
                        if existing_job["status"] in {"completed", "failed"}
                    ),
                    None,
                )
                if terminal_job_id is not None:
                    del self._jobs[terminal_job_id]

            self._jobs[job_id] = {
                "job_id": job_id,
                "status": "queued",
                "started_at": None,
                "finished_at": None,
                "count": 0,
                "results": [],
                "scan_stats": {},
                "error": None,
                "kwargs": dict(kwargs),
            }
            if self._active_price_jump_job is None:
                self._active_price_jump_job = job_id

        self._executor.submit(self._run_price_jump_scan, job_id, kwargs)
        return job_id

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        """Return a copy of a scan job, if it exists."""
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job is not None else None

    def _run_price_jump_scan(self, job_id: str, kwargs: dict[str, Any]) -> None:
        started = datetime.now(UTC).isoformat()
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job["status"] = "running"
            job["started_at"] = started
        try:
            frame = scan_price_jumps(**kwargs)
            with self._lock:
                job = self._jobs[job_id]
                job.update(
                    status="completed",
                    finished_at=datetime.now(UTC).isoformat(),
                    count=len(frame),
                    results=_records(frame),
                    scan_stats=_stats(frame),
                )
                self._active_price_jump_job = self._next_queued_price_jump_job()
                completed_at = job["finished_at"]
                results = job["results"]
                scan_stats = job["scan_stats"]
            save_completed_scan(
                job_id,
                completed_at,
                results,
                scan_stats,
            )
        except Exception as exc:
            with self._lock:
                self._jobs[job_id].update(
                    status="failed",
                    finished_at=datetime.now(UTC).isoformat(),
                    error=str(exc),
                )
                self._active_price_jump_job = self._next_queued_price_jump_job()
