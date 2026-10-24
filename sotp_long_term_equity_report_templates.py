"""
==========================================================
REPORT TEMPLATES & RISK FACTOR RESOLVER
Stage   : 16 (Presentation Layer)
Version : V1.1 (Dynamic Risk Resolution)
==========================================================

Defines default report templates, risk factors, segment-specific
risk mappings, and functional getters to prevent mutation of
shared state.
"""

from collections.abc import Sequence

DEFAULT_KEY_RISKS: list[str] = [
    "Macroeconomic slowdown impacting consumer discretionary retail spending.",
    "Commodity price volatility affecting Oil-to-Chemicals (O2C) operating margins.",
    "Regulatory shifts or spectrum auction pricing impacts on Digital Services.",
    "Execution risk on New Energy gigafactory capital expenditure timelines.",
]

SEGMENT_RISK_MAPPING = {
    "RETAIL": "Footfall fluctuations, inventory obsolescence, and margin compression from e-commerce competition.",
    "DIGITAL_SERVICES": "ARPU growth pressure, competitive churn, and elevated network infrastructure capital expenditure.",
    "OIL_TO_CHEMICALS": "Global refining margin (GRM) volatility and feed-cost cyclicality.",
    "OIL_AND_GAS": "Sub-surface exploration risks, depletion rates, and global crude price fluctuations.",
    "NEW_ENERGY": "Technology adoption velocity, regulatory tariffs, and supply chain bottlenecks for cell manufacturing.",
    "FINANCIAL_SERVICES": "Asset quality shifts, net interest margin (NIM) pressure, and credit risk exposure.",
}


def get_default_risks() -> list[str]:
    """Returns a defensive copy of the default key risks to prevent accidental mutation."""
    return DEFAULT_KEY_RISKS.copy()


def get_segment_risks(segments: Sequence[str]) -> list[str]:
    """
    Dynamically maps operating segments to relevant risk factors.
    Falls back to default risks if no segment-specific risks match.
    """
    dynamic_risks = []
    for segment in segments:
        segment_upper = str(segment).upper()
        if segment_upper in SEGMENT_RISK_MAPPING:
            dynamic_risks.append(SEGMENT_RISK_MAPPING[segment_upper])

    if not dynamic_risks:
        return get_default_risks()

    return dynamic_risks
