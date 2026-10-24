from services.valuation.comparable.comparable_input import PeerCompany
from services.valuation.comparable.multiple_calculator import calculate_multiples

p1 = PeerCompany(
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
)
m = calculate_multiples(p1)

print(
    f"DMart Multiples -> EV/Sales: {m.ev_sales:.2f}x | EV/EBITDA: {m.ev_ebitda:.2f}x | P/E: {m.pe:.2f}x | P/B: {m.pb:.2f}x"
)
