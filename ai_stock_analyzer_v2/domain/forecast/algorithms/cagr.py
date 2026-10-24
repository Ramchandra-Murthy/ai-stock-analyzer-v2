from __future__ import annotations

from decimal import Decimal


class CAGRCalculator:
    """Pure domain calculation engine for Compound Annual Growth Rate forecasting."""

    @staticmethod
    def calculate(
        historical_values: tuple[Decimal, ...], periods_to_forecast: int
    ) -> tuple[Decimal, ...]:
        if not historical_values or len(historical_values) < 2:
            raise ValueError("At least two historical data points are required for CAGR.")

        start_val = historical_values[0]
        end_val = historical_values[-1]
        n = len(historical_values) - 1

        if start_val <= 0 or end_val <= 0:
            raise ValueError("Historical values must be positive for CAGR calculation.")

        cagr = (end_val / start_val) ** (Decimal("1") / Decimal(n)) - Decimal("1")

        projected = []
        current = end_val
        for _ in range(periods_to_forecast):
            current = current * (Decimal("1") + cagr)
            projected.append(current.quantize(Decimal("0.01")))

        return tuple(projected)
