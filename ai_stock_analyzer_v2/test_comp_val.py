from services.valuation.comparable.comparable_input import (
    ComparableInput,
    PeerCompany,
    TargetCompany,
)
from services.valuation.comparable.validation import validate_input

t = TargetCompany("Reliance Retail", 100000.0, 8000.0, 12000.0, 5000.0, 30000.0, 2000.0, 1000.0)
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

try:
    validate_input(ComparableInput(target=t, peers=[p1, p1]))
except ValueError as e:
    print(f"Validation Caught Error Successfully: {e}")

validate_input(ComparableInput(target=t, peers=[p1]))
print("Valid Input Passed Successfully!")
