from __future__ import annotations

from core.primitives.fiscal import FiscalPeriod, Frequency


def run_example() -> None:
    print("--- CORE-001B: Fiscal & Time Types Example ---")
    fy = FiscalPeriod(year=2026, frequency=Frequency.ANNUAL)
    q_report = FiscalPeriod(year=2026, quarter=1, frequency=Frequency.QUARTERLY)

    print(f"Annual Reporting Period: FY{fy.year} ({fy.frequency})")
    print(
        f"Quarterly Reporting Period: FY{q_report.year} Q{q_report.quarter} ({q_report.frequency})"
    )


if __name__ == "__main__":
    run_example()
