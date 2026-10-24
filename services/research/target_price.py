from __future__ import annotations

from dataclasses import dataclass

from core.enums import Status, ValuationMethod
from core.exceptions import ValuationError
from core.logger import logger


@dataclass(slots=True, frozen=True)
class TargetPriceOutput:
    ticker: str
    current_market_price: float
    weighted_fair_value: float
    target_price: float
    implied_upside_pct: float
    status: Status = Status.OK


class TargetPriceCalculator:
    """Computes weighted fair value and applies margin of safety buffers."""

    @staticmethod
    def compute_target_price(
        ticker: str,
        current_market_price: float,
        method_values: dict[ValuationMethod, float],
        method_weights: dict[ValuationMethod, float],
        margin_of_safety_pct: float = 0.10,
    ) -> TargetPriceOutput:
        if not method_values:
            raise ValuationError("At least one valuation method output is required.")

        total_weight = sum(method_weights.get(m, 0.0) for m in method_values.keys())
        if abs(total_weight - 1.0) > 1e-4:
            raise ValuationError(
                f"Valuation method weights must sum to 1.0 (got {total_weight:.4f})."
            )

        weighted_fair_value = sum(
            val * method_weights[method] for method, val in method_values.items()
        )
        target_price = weighted_fair_value * (1.0 - margin_of_safety_pct)
        implied_upside = (target_price - current_market_price) / max(current_market_price, 1e-4)

        logger.info(
            f"[{ticker}] Fair Value: {weighted_fair_value:.2f} | Target: {target_price:.2f} | Upside: {implied_upside:.2%}"
        )

        return TargetPriceOutput(
            ticker=ticker,
            current_market_price=current_market_price,
            weighted_fair_value=round(weighted_fair_value, 2),
            target_price=round(target_price, 2),
            implied_upside_pct=round(implied_upside, 4),
        )
