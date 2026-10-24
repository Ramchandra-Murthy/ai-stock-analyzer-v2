from services.financials.balance_sheet import BalanceSheet
from services.financials.cash_flow import CashFlowStatement
from services.financials.financial_ratios import calculate_financial_ratios
from services.financials.income_statement import IncomeStatement

inc = IncomeStatement(
    revenue=100000.0,
    cost_of_goods_sold=60000.0,
    ebitda=20000.0,
    ebit=16000.0,
    net_income=10500.0,
)

bs = BalanceSheet(
    cash=5000.0,
    accounts_receivable=10000.0,
    inventory=8000.0,
    total_current_assets=35000.0,
    total_assets=120000.0,
    total_current_liabilities=20000.0,
    short_term_debt=4000.0,
    long_term_debt=16000.0,
    total_equity=75000.0,
)

cf = CashFlowStatement(operating_cash_flow=15000.0, capital_expenditure=4000.0)

ratios = calculate_financial_ratios(inc, bs, cf)

print("=== RATIO ENGINE VERIFICATION ===")
print(f"Gross Margin    : {ratios.gross_margin:.2%}")
print(f"EBITDA Margin   : {ratios.ebitda_margin:.2%}")
print(f"ROE             : {ratios.roe:.2%}")
print(f"ROIC            : {ratios.roic:.2%}")
print(f"Current Ratio   : {ratios.current_ratio:.2f}x")
print(f"Quick Ratio     : {ratios.quick_ratio:.2f}x")
print(f"Net Debt/EBITDA : {ratios.net_debt_to_ebitda:.2f}x")
print(f"Cash Conversion : {ratios.cash_conversion_ratio:.2f}x")
