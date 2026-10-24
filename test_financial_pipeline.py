from services.financials.builders import ValuationPayloadBuilder
from services.financials.parser import FinancialStatementParser
from services.financials.repository import FinancialRepository

# Raw filing input payload (simulating an ingested annual report)
filing_data = {
    "company_name": "Larsen & Toubro",
    "ticker": "LT.NS",
    "currency": "INR",
    "periods": [
        {
            "period": "FY2026",
            "income_statement": {
                "revenue": 220000.0,
                "cost_of_goods_sold": 150000.0,
                "operating_expenses": 45000.0,
                "depreciation_amortization": 5000.0,
                "shares_outstanding": 1400.0,
            },
            "balance_sheet": {
                "cash_and_equivalents": 12000.0,
                "short_term_debt": 5000.0,
                "long_term_debt": 35000.0,
                "total_assets": 310000.0,
                "total_liabilities": 200000.0,
                "total_equity": 110000.0,
            },
            "cash_flow": {
                "operating_cash_flow": 28000.0,
                "capital_expenditures": 9000.0,
            },
        }
    ],
}

# 1. Parse Filing
sfdm = FinancialStatementParser.parse_dict(filing_data)

# 2. Store in Repository
repo = FinancialRepository()
repo.save(sfdm)
retrieved = repo.get_by_ticker("LT.NS")

# 3. Build Engine Payloads
dcf_payload = ValuationPayloadBuilder.build_dcf_input(retrieved)
cca_target = ValuationPayloadBuilder.build_cca_target(retrieved)

print("=== SFDM PARSER & BUILDER VERIFICATION ===")
print(f"Repository Record : {retrieved.company_name} ({retrieved.ticker})")
print(f"DCF Revenue Input : ₹{dcf_payload['revenue']:,.2f} Cr")
print(f"CCA Target Net Debt: ₹{cca_target['net_debt']:,.2f} Cr")
