from services.valuation.comparable.comparable_input import (
    ComparableInput,
    PeerCompany,
    TargetCompany,
)
from services.valuation.comparable.comparable_model import ComparableModel

target = TargetCompany(
    company_name="Reliance Retail",
    revenue=100000.0,
    ebit=8000.0,
    ebitda=12000.0,
    net_income=5000.0,
    book_value=30000.0,
    net_debt=20000.0,
    shares_outstanding=1000.0,
)

peers = [
    PeerCompany(
        "DMart",
        "DMART.NS",
        200000.0,
        190000.0,
        40000.0,
        3000.0,
        4500.0,
        2000.0,
        15000.0,
        600.0,
        316.0,
    ),
    PeerCompany(
        "Trent",
        "TRENT.NS",
        150000.0,
        140000.0,
        12000.0,
        1100.0,
        1800.0,
        800.0,
        5000.0,
        350.0,
        400.0,
    ),
    PeerCompany(
        "V-Mart",
        "VMART.NS",
        8000.0,
        7500.0,
        2500.0,
        150.0,
        300.0,
        100.0,
        800.0,
        20.0,
        375.0,
    ),
]

model = ComparableModel(ComparableInput(target=target, peers=peers))
res = model.run_model()

print("=== WEIGHTED VALUATION RESULTS ===")
print(f"Weighted Recommended EV    : ₹{res.recommended_enterprise_value:,.2f} Cr")
print(f"Weighted Recommended Equity: ₹{res.recommended_equity_value:,.2f} Cr")
print(f"Weighted Share Price       : ₹{res.implied_share_price:,.2f}")
