from __future__ import annotations

"""
==========================================================
PLATFORM VERSION & METADATA
Module  : core.version
Version : 4.0.0
==========================================================
"""

PLATFORM_NAME = "AI Institutional Equity Research Platform"
PLATFORM_VERSION = "4.0.0"
AUTHOR = "Ramchandra Murthy"
BUILD = "2026.08"
PYTHON_VERSION = "3.13+"
ARCHITECTURE = "Modular Institutional Valuation Platform"


def get_version_info() -> dict[str, str]:
    return {
        "platform_name": PLATFORM_NAME,
        "version": PLATFORM_VERSION,
        "author": AUTHOR,
        "build": BUILD,
        "python_version": PYTHON_VERSION,
        "architecture": ARCHITECTURE,
    }
