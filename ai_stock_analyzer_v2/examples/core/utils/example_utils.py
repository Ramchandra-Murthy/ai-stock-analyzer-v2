from __future__ import annotations

from decimal import Decimal

from core.utils import NumberFormatter, get_logger


def run_example() -> None:
    print("--- CORE-006: Utilities Example ---")
    logger = get_logger("CORE-006-Demo")
    logger.info("Initializing utility demonstration...")

    formatted_money = NumberFormatter.format_currency(Decimal("4500000.00"), "INR")
    formatted_pct = NumberFormatter.format_percentage(Decimal("15.75"))

    print(f"Formatted Money: {formatted_money}")
    print(f"Formatted Percentage: {formatted_pct}")


if __name__ == "__main__":
    run_example()
