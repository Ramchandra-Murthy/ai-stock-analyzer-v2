from dataclasses import dataclass
from typing import Any


@dataclass
class DCFInput:
    """
    Input data container for the Discounted Cash Flow (DCF) valuation engine.
    Includes strict validation to ensure structural and economic sanity.
    """

    # Historical Base
    last_historical_revenue: float

    # Forecast Driver Vectors (Must all match forecast period length)
    revenue_growth_rates: list[float]
    ebit_margin_forecast: list[float]
    capex_pct_rev: list[float]
    nwc_pct_rev: list[float]
    dna_pct_rev: list[float]

    # Capital Structure & Discount Parameters
    tax_rate: float
    cost_of_equity: float
    cost_of_debt_post_tax: float
    equity_weight: float
    debt_weight: float

    # Terminal Value Parameter
    terminal_growth_rate: float

    # Capital Structure Bridge to Equity Value
    total_debt: float
    cash_and_equivalents: float
    shares_outstanding: float

    # Non-Operating Balance Sheet Adjustments
    minority_interest: float = 0.0
    preferred_stock: float = 0.0

    # Optional metadata
    company_name: str = "Operating Subsidiary"
    currency: str = "INR"

    @property
    def forecast_years(self) -> int:
        """
        Dynamically returns the number of explicit forecast years.
        """
        return len(self.revenue_growth_rates)

    def calculate_wacc(self) -> float:
        """
        Calculates the Weighted Average Cost of Capital (WACC).
        WACC = (We * Ke) + (Wd * Kd_post_tax)
        """
        return (self.equity_weight * self.cost_of_equity) + (
            self.debt_weight * self.cost_of_debt_post_tax
        )

    def validate(self) -> None:
        """
        Executes comprehensive input validation checks before model execution.
        """
        forecast_len = self.forecast_years
        if forecast_len == 0:
            raise ValueError("Forecast period must be at least 1 year long.")

        vectors = {
            "ebit_margin_forecast": len(self.ebit_margin_forecast),
            "capex_pct_rev": len(self.capex_pct_rev),
            "nwc_pct_rev": len(self.nwc_pct_rev),
            "dna_pct_rev": len(self.dna_pct_rev),
        }
        for vec_name, length in vectors.items():
            if length != forecast_len:
                raise ValueError(
                    f"Array length mismatch for '{vec_name}': expected {forecast_len}, got {length}."
                )

        if self.last_historical_revenue <= 0:
            raise ValueError("last_historical_revenue must be strictly greater than 0.")
        if self.shares_outstanding <= 0:
            raise ValueError("shares_outstanding must be strictly greater than 0.")
        if self.total_debt < 0:
            raise ValueError("total_debt cannot be negative.")
        if self.cash_and_equivalents < 0:
            raise ValueError("cash_and_equivalents cannot be negative.")

        if not (0.0 <= self.tax_rate <= 1.0):
            raise ValueError(f"tax_rate must be between 0.0 and 1.0 (got {self.tax_rate}).")

        weight_sum = self.equity_weight + self.debt_weight
        if abs(weight_sum - 1.0) > 1e-4:
            raise ValueError(f"Equity and Debt weights must sum to 1.0 (got {weight_sum:.4f}).")

        wacc = self.calculate_wacc()
        if self.terminal_growth_rate >= wacc:
            raise ValueError(
                f"Terminal growth rate ({self.terminal_growth_rate:.2%}) must be strictly less "
                f"than WACC ({wacc:.2%}) to prevent mathematical singularity."
            )

    def to_dict(self) -> dict[str, Any]:
        """Returns assumptions as a dictionary."""
        return {
            "last_historical_revenue": self.last_historical_revenue,
            "forecast_years": self.forecast_years,
            "revenue_growth_rates": self.revenue_growth_rates,
            "ebit_margin_forecast": self.ebit_margin_forecast,
            "wacc": self.calculate_wacc(),
            "terminal_growth_rate": self.terminal_growth_rate,
            "shares_outstanding": self.shares_outstanding,
        }
