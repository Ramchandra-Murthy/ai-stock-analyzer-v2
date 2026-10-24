from services.financials.normalization import normalize_financial_statements
from services.financials.repository import FinancialStatementRepository

repo = FinancialStatementRepository()

fs = normalize_financial_statements(
    company_name="State Bank of India",
    ticker="SBIN.NS",
    currency="INR",
    fiscal_year="FY2026",
    income_raw={"totalRevenue": 380000.0, "sharesOutstanding": 8920.0},
    balance_raw={
        "totalAssets": 6000000.0,
        "totalLiabilities": 5600000.0,
        "shareholdersEquity": 400000.0,
    },
    cashflow_raw={"operatingCashFlow": 45000.0},
)

print("=== REPOSITORY PATTERN VERIFICATION ===")

# Save
repo.save(fs)
print(f"✓ Saved: {fs.company_name} ({fs.fiscal_year})")

# Exists & Load
if repo.exists("State Bank of India", "FY2026"):
    loaded = repo.load("State Bank of India", "FY2026")
    print(f"✓ Loaded: {loaded.company_name} | Assets: ₹{loaded.balance_sheet.total_assets:,.2f} Cr")

# List Companies
keys = repo.list_companies()
print(f"✓ Active Repository Keys: {keys}")

# Delete
deleted = repo.delete("State Bank of India", "FY2026")
print(f"✓ Deleted: {deleted} | Remaining Keys: {repo.list_companies()}")
