from __future__ import annotations

import logging
import sys
from typing import Any

from core.enums import Status

# Base Logger Configuration
logger = logging.getLogger("equity_platform")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class AuditTrail:
    """Context manager for audit logging telemetry."""

    def __init__(
        self,
        operation_name: str = "VALUATION",
        ticker: str = "",
        method: str = "",
        execution_id: str = "",
        **kwargs,
    ):
        self.operation_name = operation_name
        self.ticker = ticker
        self.method = method
        self.execution_id = execution_id
        self.steps: list[dict[str, Any]] = []
        self.status = Status.OK

    def add_step(
        self,
        step_name: str,
        status: Status = Status.OK,
        details: dict[str, Any] | None = None,
    ):
        self.steps.append({"step": step_name, "status": status, "details": details or {}})

    def __enter__(self):
        logger.info(
            f"[AUDIT START] {self.operation_name} | Ticker: {self.ticker} | Execution ID: {self.execution_id}"
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.status = Status.FAILED
            logger.error(f"[AUDIT FAILED] {self.operation_name} | Exception: {exc_val}")
        else:
            logger.info(f"[AUDIT END] {self.operation_name} | Status: {self.status.value}")
        return False
