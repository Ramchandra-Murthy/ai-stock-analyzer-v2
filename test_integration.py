from services.valuation.contracts import SOTPSegmentInput
from services.valuation.models import ValuationMethod, ValuationStatus
from services.valuation.sotp_engine import SOTPEngine

engine = SOTPEngine(group_name="Conglomerate Holdings", total_group_shares=100.0)

entities = [
    SOTPSegmentInput(
        segment_name="Operating Core (DCF)",
        valuation_method=ValuationMethod.DCF,
        last_historical_revenue=1500.0,
        revenue_growth_rates=[0.12, 0.10, 0.08, 0.06, 0.05],
        segment_debt=200.0,
        segment_cash=80.0,
        shares_outstanding=100.0,
    ),
    SOTPSegmentInput(
        segment_name="Real Estate Arm (NAV)",
        valuation_method=ValuationMethod.NAV,
    ),
    SOTPSegmentInput(
        segment_name="Strategic Investment (Market)",
        valuation_method=ValuationMethod.MARKET,
    ),
    SOTPSegmentInput(
        segment_name="Legacy Asset (Book)",
        valuation_method=ValuationMethod.BOOK_VALUE,
    ),
]

results = engine.evaluate_group(entities)

print("\n=== Registry-Driven Dispatcher Verification ===")
for r in results:
    status_tag = f"[{r.valuation_status.value}]"
    if r.valuation_status == ValuationStatus.COMPLETE:
        print(
            f"{r.entity_name:<30} | {r.valuation_method.value:<10} | {status_tag:<12} | EV: {r.enterprise_value:,.2f} | WACC: {r.diagnostics.get('wacc', 0):.2%}"
        )
    else:
        print(
            f"{r.entity_name:<30} | {r.valuation_method.value:<10} | {status_tag:<12} | {r.diagnostics.get('error', 'Pending implementation')}"
        )
