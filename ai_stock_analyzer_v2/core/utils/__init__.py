from __future__ import annotations

import logging


def format_currency(amount: float, currency: str = "INR") -> str:
    return f"{currency} {amount:,.2f}"


def round_currency(amount: float, decimals: int = 2) -> float:
    return round(amount, decimals)


class NumberFormatter:
    @staticmethod
    def format_decimal(value: float, decimals: int = 2) -> str:
        return f"{float(value):.{decimals}f}"

    @staticmethod
    def format_currency(amount: float, currency: str = "INR") -> str:
        return f"{currency} {float(amount):,.2f}"

    @staticmethod
    def format_percentage(value: float, decimals: int = 2) -> str:
        return f"{float(value):.{decimals}f}%"


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
