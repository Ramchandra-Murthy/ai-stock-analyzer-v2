from __future__ import annotations

from datetime import date

from core.value_objects import DateRange, FiscalPeriod


def run_example() -> None:
    print("--- CORE-001B: Time & Fiscal Types Example ---")
    period = FiscalPeriod.from_ints(2026, "Q1")
    quarter_range = DateRange(date(2026, 4, 1), date(2026, 6, 30))

    print(f"Active Fiscal Period: {period}")
    print(
        f"Period Date Range: {quarter_range.start_date} to {quarter_range.end_date} ({quarter_range.duration_days()} days)"
    )
    print(f"Serialized Period: {period.to_dict()}")


if __name__ == "__main__":
    run_example()
