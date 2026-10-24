from __future__ import annotations

"""
==========================================================
DCF VALUATION PACKAGE
Module  : dcf
Version : V3.1
==========================================================

Provides institutional Discounted Cash Flow (DCF) modeling.
"""

from services.valuation.dcf.dcf_input import DCFInput
from services.valuation.dcf.dcf_model import DCFModel
from services.valuation.dcf.dcf_result import DCFResult
from services.valuation.dcf.discounting import (
    DiscountSchedule,
    build_discount_schedule,
)
from services.valuation.dcf.forecast import (
    ForecastSchedule,
    build_forecast_schedule,
    forecast_revenue,
)
from services.valuation.dcf.sensitivity import (
    SensitivityResult,
    build_sensitivity_matrix,
)
from services.valuation.dcf.terminal_value import (
    TerminalValueResult,
    build_terminal_value,
)
from services.valuation.dcf.validation import validate_input


def run_dcf(data: DCFInput) -> DCFResult:
    """
    Convenience wrapper around DCFModel.
    Executes end-to-end validation, forecasting, discounting,
    terminal value calculation, equity bridge, and sensitivity analysis.
    """
    return DCFModel(data).run_model()


__all__ = [
    "DCFInput",
    "DCFResult",
    "DCFModel",
    "run_dcf",
    "validate_input",
    "ForecastSchedule",
    "forecast_revenue",
    "build_forecast_schedule",
    "DiscountSchedule",
    "build_discount_schedule",
]

__all__.extend(
    [
        "TerminalValueResult",
        "build_terminal_value",
    ]
)

__all__.extend(
    [
        "SensitivityResult",
        "build_sensitivity_matrix",
    ]
)
