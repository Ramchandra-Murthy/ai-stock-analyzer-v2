from __future__ import annotations

from decimal import Decimal


class NumberFormatter:
    @staticmethod
    def format_currency(amount: Decimal, currency_code: str = "INR") -> str:
        """Formats a decimal amount into a readable currency string."""
        return f"{amount:,.2f} {currency_code}"

    @staticmethod
    def format_percentage(value: Decimal) -> str:
        """Formats a decimal percentage."""
        return f"{value:.2f}%"
