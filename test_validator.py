from services.financials.normalization import normalize_financial_statements
from services.financials.validator import validate_financial_statements

print("=== VALIDATOR VERIFICATION ===")

# 1. Valid Normalized Financial Statement
valid_fs = normalize_financial_statements(
    company_name="Tata Consultancy Services",
    ticker="TCS.NS",
    currency="INR",
    fiscal_year="FY2026",
    income_raw={"totalRevenue": 240000.0, "sharesOutstanding": 3600.0},
    balance_raw={
        "totalAssets": 150000.0,
        "totalLiabilities": 50000.0,
        "totalEquity": 100000.0,
    },
    cashflow_raw={"operatingCashFlow": 40000.0},
)

try:
    validate_financial_statements(valid_fs)
    print("✓ Valid Financial Statements passed validation successfully.")
except ValueError as e:
    print(f"✗ Validation unexpectedly failed: {e}")

# 2. Broken Accounting Identity
invalid_fs = normalize_financial_statements(
    company_name="Corrupt Data Corp",
    ticker="BAD.NS",
    currency="INR",
    fiscal_year="FY2026",
    income_raw={"totalRevenue": 100.0, "sharesOutstanding": 10.0},
    balance_raw={
        "totalAssets": 1000.0,
        "totalLiabilities": 400.0,
        "totalEquity": 500.0,
    },  # Diff = 100
    cashflow_raw={},
)

try:
    validate_financial_statements(invalid_fs)
    print("✗ Failed to catch accounting identity error.")
except ValueError as e:
    print("✓ Correctly caught broken accounting identity:")
    print("  " + str(e).replace("\n", " | "))
