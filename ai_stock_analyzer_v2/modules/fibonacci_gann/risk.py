"""Conservative, deterministic position sizing for the Fibonacci/Gann lab.

Costs are caller-supplied estimates per unit for the complete trade (fees plus
slippage). This helper is educational and does not submit or recommend orders.
"""

from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal

from modules.fibonacci_gann.levels import Price


@dataclass(frozen=True)
class PositionSize:
    """Position size and estimated risk in the same currency units as inputs."""

    quantity: int
    entry_price: Decimal
    stop_price: Decimal
    risk_per_unit: Decimal
    estimated_loss: Decimal
    capital_required: Decimal
    capital_limit: Decimal
    risk_limit: Decimal


def _positive_decimal(value: Price, name: str, *, allow_zero: bool = False) -> Decimal:
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (ArithmeticError, ValueError) as exc:
        qualifier = "non-negative" if allow_zero else "positive"
        raise ValueError(f"{name} must be a finite {qualifier} value") from exc
    if not result.is_finite():
        qualifier = "non-negative" if allow_zero else "positive"
        raise ValueError(f"{name} must be a finite {qualifier} value")
    invalid = result < 0 if allow_zero else result <= 0
    if invalid:
        qualifier = "non-negative" if allow_zero else "positive"
        raise ValueError(f"{name} must be a finite {qualifier} value")
    return result


def calculate_position_size(
    entry_price: Price,
    stop_price: Price,
    *,
    capital: Price = "10000",
    max_loss: Price = "500",
    cost_per_unit: Price = "0",
) -> PositionSize:
    """Size a long position under both capital and estimated-loss ceilings.

    cost_per_unit must estimate total round-trip fees and slippage per unit.
    Quantity is rounded down to a whole unit. This models long positions only;
    entry must be above the stop. It does not model options lot sizes, turnover-
    dependent taxes, price gaps, or guaranteed stop execution.
    """
    entry = _positive_decimal(entry_price, "entry_price")
    stop = _positive_decimal(stop_price, "stop_price")
    available_capital = _positive_decimal(capital, "capital")
    loss_limit = _positive_decimal(max_loss, "max_loss")
    unit_cost = _positive_decimal(cost_per_unit, "cost_per_unit", allow_zero=True)

    if stop >= entry:
        raise ValueError("stop_price must be below entry_price for a long position")
    if loss_limit > available_capital:
        raise ValueError("max_loss cannot exceed available capital")

    unit_risk = entry - stop + unit_cost
    risk_quantity = (loss_limit / unit_risk).to_integral_value(rounding=ROUND_FLOOR)
    capital_quantity = (available_capital / entry).to_integral_value(rounding=ROUND_FLOOR)
    quantity = int(min(risk_quantity, capital_quantity))
    estimated_loss = unit_risk * quantity
    capital_required = entry * quantity

    if quantity < 1:
        raise ValueError("risk and capital limits do not permit even one unit")

    return PositionSize(
        quantity=quantity,
        entry_price=entry,
        stop_price=stop,
        risk_per_unit=unit_risk,
        estimated_loss=estimated_loss,
        capital_required=capital_required,
        capital_limit=available_capital,
        risk_limit=loss_limit,
    )
