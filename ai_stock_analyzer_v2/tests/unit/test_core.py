from __future__ import annotations

import pytest

from core.enums import Status, ValuationMethod
from core.exceptions import PlatformError, ValidationError, ValuationError
from core.logger import AuditTrail
from core.settings import settings
from core.version import get_version_info


def test_version_metadata():
    version_data = get_version_info()
    assert version_data["version"] == "4.0.0"


def test_exception_hierarchy():
    val_err = ValidationError("Identity mismatch", {"discrepancy": 100.0})
    assert isinstance(val_err, PlatformError)
    assert val_err.details["discrepancy"] == 100.0


def test_settings_immutability():
    with pytest.raises(AttributeError):
        settings.dcf.DEFAULT_TAX_RATE = 0.30


def test_audit_trail_success_flow():
    with AuditTrail(ticker="LT.NS", method=ValuationMethod.DCF, execution_id="EXEC-101") as audit:
        audit.add_step("CALCULATE_WACC", Status.OK, {"wacc": 0.1082})
    assert audit.status == Status.OK


def test_audit_trail_failure_flow():
    with pytest.raises(ValuationError):
        with AuditTrail(
            ticker="LT.NS", method=ValuationMethod.DCF, execution_id="EXEC-102"
        ) as audit:
            raise ValuationError("Boundary error")
    assert audit.status == Status.FAILED
