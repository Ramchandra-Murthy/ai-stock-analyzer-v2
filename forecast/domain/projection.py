from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from core.primitives.base import ValueObject
from core.validation import validate_non_empty_string, validate_non_negative


@dataclass(frozen=True, order=True)
class FinancialProjection(ValueObject):
    """Immutable representation of a multi-period financial projection."""

    period_label: str
    projected_revenue: Decimal
    projected_ebitda: Decimal
    confidence_score: Decimal  # Between 0.0 and 1.0

    def __post_init__(self) -> None:
        validate_non_empty_string(self.period_label, "Period Label")
        validate_non_negative(self.projected_revenue, "Projected Revenue")
        validate_non_negative(self.projected_ebitda, "Projected EBITDA")
        validate_non_negative(self.confidence_score, "Confidence Score")

        if self.confidence_score > Decimal("1.0"):
            raise ValueError("Confidence score cannot exceed 1.0.")

        object.__setattr__(self, "period_label", self.period_label.strip().upper())
        object.__setattr__(self, "projected_revenue", Decimal(str(self.projected_revenue)))
        object.__setattr__(self, "projected_ebitda", Decimal(str(self.projected_ebitda)))
        object.__setattr__(self, "confidence_score", Decimal(str(self.confidence_score)))

    def ebitda_margin(self) -> Decimal:
        """Calculates projected EBITDA margin."""
        if self.projected_revenue == 0:
            return Decimal("0.0")
        return (self.projected_ebitda / self.projected_revenue) * Decimal("100")

    def to_dict(self) -> dict[str, Any]:
        return {
            "period_label": self.period_label,
            "projected_revenue": str(self.projected_revenue),
            "projected_ebitda": str(self.projected_ebitda),
            "confidence_score": str(self.confidence_score),
            "ebitda_margin": str(self.ebitda_margin()),
        }
