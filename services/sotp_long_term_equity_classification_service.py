from dataclasses import dataclass

from services.sotp_long_term_equity_domain_constants import (
    CLASSIFICATION_OPERATING_INFRASTRUCTURE,
    CLASSIFICATION_UNRESOLVED,
    INTERPRETATION_OPERATING_INFRASTRUCTURE,
)


@dataclass(frozen=True)
class ClassificationRule:
    """
    Declarative rule definition mapping economic interpretation and
    optional contextual attributes to target SOTP classifications.
    """

    interpretation: str
    relationship: str | None = None

    # --- Future Domain Dimensions (Optional Predicates) ---
    business_model: str | None = None
    asset_type: str | None = None
    integration_level: str | None = None

    classification: str = CLASSIFICATION_UNRESOLVED
    priority: int = 1


class ClassificationRuleEvaluator:
    """Evaluates interpreted evidence against declarative rules."""

    def __init__(self, custom_rules: list[ClassificationRule] | None = None) -> None:
        # Standard default rules
        self.rules: list[ClassificationRule] = custom_rules or [
            # Example rule with extended dimensions
            ClassificationRule(
                interpretation=INTERPRETATION_OPERATING_INFRASTRUCTURE,
                asset_type="PIPELINE_NETWORK",
                classification=CLASSIFICATION_OPERATING_INFRASTRUCTURE,
                priority=95,
            ),
            # Standard rules...
        ]

    def find_best_rule(
        self,
        interpretation: str,
        ril_relationship: str | None,
        business_model: str | None = None,
        asset_type: str | None = None,
        integration_level: str | None = None,
    ) -> list[ClassificationRule]:
        matched_rules = []
        for rule in self.rules:
            # Mandated Interpretation Match
            if rule.interpretation != interpretation:
                continue

            # Optional Contextual Attribute Checks (None acts as wildcard)
            if rule.relationship is not None and rule.relationship != ril_relationship:
                continue
            if rule.business_model is not None and rule.business_model != business_model:
                continue
            if rule.asset_type is not None and rule.asset_type != asset_type:
                continue
            if rule.integration_level is not None and rule.integration_level != integration_level:
                continue

            matched_rules.append(rule)
        return matched_rules
