from services.valuation.dcf_engine import DCFEngine
from services.valuation.dispatcher import ValuationDispatcher
from services.valuation.sotp_engine import SOTPEngine
from services.valuation.stub_adapters import (
    BookValueEngine,
    MarketValuationEngine,
    NAVValuationEngine,
)

# 1. Startup: Instantiate Dispatcher & Register Engines
dispatcher = ValuationDispatcher()
dispatcher.register(DCFEngine())
dispatcher.register(NAVValuationEngine())
dispatcher.register(MarketValuationEngine())
dispatcher.register(BookValueEngine())

# 2. Define Entities with Polymorphic Payload Specs
my_entities = [
    {
        "segment_name": "Operating Core (Tech)",
        "valuation_method": "DCF",
        "historical_revenue": 1000.0,
        "revenue_growth_rates": [0.15, 0.12, 0.10, 0.08, 0.06],
        "ebit_margin_forecast": [0.22, 0.23, 0.24, 0.25, 0.25],
        "depreciation_pct_revenue": 0.03,
        "capex_pct_revenue": 0.04,
        "nwc_pct_revenue": 0.05,
        "tax_rate": 0.25,
        "cost_of_equity": 0.12,
        "cost_of_debt_post_tax": 0.06,
        "equity_weight": 0.8,
        "debt_weight": 0.2,
        "terminal_growth_rate": 0.03,
        "segment_debt": 100.0,
        "segment_cash": 250.0,
        "shares_outstanding": 100.0,
    },
    {
        "segment_name": "Real Estate Division",
        "valuation_method": "NAV",
    },
    {
        "segment_name": "Strategic Listed Holding",
        "valuation_method": "MARKET",
    },
    {
        "segment_name": "Distressed Banking Arm",
        "valuation_method": "BOOK_VALUE",
    },
]

# 3. Execute SOTP Valuation
engine = SOTPEngine(dispatcher)
result = engine.value(
    entities=my_entities,
    net_debt=250.0,
    shares_outstanding=100.0,
    holdco_discount=0.15,
)

# 4. Display Results
print("=== SOTP VALUATION SUMMARY ===")
print(f"Group Enterprise Value : {result.enterprise_value:,.2f}")
print(f"Group Equity Value     : {result.equity_value:,.2f}")
print(f"Implied Price per Share: {result.implied_share_price:,.2f}\n")

print(f"{'Segment Name':<30} | {'Method':<10} | {'Status':<10} | {'Enterprise Value'}")
print("-" * 75)
for res in result.component_results:
    print(
        f"{res.entity_name:<30} | {res.valuation_method.value:<10} | {res.valuation_status.value:<10} | {res.enterprise_value:15,.2f}"
    )
