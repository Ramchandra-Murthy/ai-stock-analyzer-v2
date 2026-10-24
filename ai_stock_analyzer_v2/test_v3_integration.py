from services.financials.builders import build_comparable_input, build_dcf_input
from services.financials.financial_ratios import calculate_financial_ratios
from services.financials.parser import (
    get_financial_statements,
    parse_financial_statements,
)

print("==========================================================")
print("FINANCIAL STATEMENT LAYER (V3.0) - END-TO-END VERIFICATION")
print("==========================================================")

raw_inc = {
    "totalRevenue": 220000.0,
    "costOfRevenue": 130000.0,
    "ebitda": 38000.0,
    "operatingIncome": 30000.0,
    "netIncome": 21000.0,
    "sharesOutstanding": 1400.0,
    "depreciation": 8000.0,
}

raw_bs = {
    "cash": 15000.0,
    "shortTermInvestments": 10000.0,
    "propertyPlantEquipment": 45000.0,
    "goodwill": 8000.0,
    "totalAssets": 250000.0,
    "shortTermDebt": 5000.0,
    "longTermDebt": 25000.0,
    "totalLiabilities": 100000.0,
    "shareholdersEquity": 150000.0,
}

raw_cf = {
    "operatingCashFlow": 28000.0,
    "capex": 9000.0,
    "investingCashFlow": -12000.0,
    "financingCashFlow": -8000.0,
}

fs = parse_financial_statements(
    company_name="Larsen & Toubro",
    ticker="LT.NS",
    currency="INR",
    fiscal_year="FY2026",
    income_statement=raw_inc,
    balance_sheet=raw_bs,
    cash_flow=raw_cf,
)

print(f"✓ Ingestion & Validation Success: {fs.company_name} ({fs.ticker})")

retrieved = get_financial_statements("Larsen & Toubro", "FY2026")
print(
    f"✓ Repository Retrieval         : Net Income = ₹{retrieved.income_statement.net_income:,.2f} Cr"
)

ratios = calculate_financial_ratios(
    retrieved.income_statement, retrieved.balance_sheet, retrieved.cash_flow_statement
)
print(
    f"✓ Analytics Layer               : ROE = {ratios.roe:.2%} | Net Debt/EBITDA = {ratios.net_debt_to_ebitda:.2f}x"
)

dcf_in = build_dcf_input(retrieved)
print(
    f"✓ DCF Builder Input             : Forecast Horizon = {len(dcf_in.revenue_growth_rates)} Yrs | Last Revenue = ₹{dcf_in.last_historical_revenue:,.2f} Cr"
)

comp_in = build_comparable_input(retrieved)
print(f"✓ Comparable Builder Input       : Target EBITDA Base = ₹{comp_in.target.ebitda:,.2f} Cr")

print("==========================================================")
print("ALL SYSTEMS OPERATIONAL: Financial Statement Layer V1.0 Ready!")
print("==========================================================")
