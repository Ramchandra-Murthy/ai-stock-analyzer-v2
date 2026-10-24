"""Capital valuation compatibility package."""

__all__ = ["CAPMOutput", "CapitalCostEngine"]


def __getattr__(name: str):
    if name in __all__:
        from .wacc_engine import CapitalCostEngine, CAPMOutput

        return {"CAPMOutput": CAPMOutput, "CapitalCostEngine": CapitalCostEngine}[name]
    raise AttributeError(name)
