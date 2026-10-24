from services.valuation.comparable.comparable_input import PeerCompany
from services.valuation.comparable.peer_selection import select_peers

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
p1_dup = PeerCompany(
    "DMart Duplicate",
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
p_invalid = PeerCompany(
    "BadPeer",
    "BAD.NS",
    -100.0,
    190000.0,
    40000.0,
    3000.0,
    4500.0,
    2000.0,
    15000.0,
    600.0,
    316.0,
)

res = select_peers([p1, p1_dup, p_invalid])
print(f"Input: 3 peers | Selected: {len(res)} peer ({res[0].name})")
