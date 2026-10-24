"""Compatibility facade for the canonical AI component scorer.

The final investment recommendation is intentionally not produced here.
Use services.recommendation_service.generate_recommendation().
"""

from services.ai_service import get_ai_recommendation

__all__ = ["get_ai_recommendation"]
