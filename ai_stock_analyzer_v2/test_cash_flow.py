from services.financials.cash_flow import CashFlowStatement

cf = CashFlowStatement(
    operating_cash_flow=18500.0,
    capital_expenditure=4200.0,
    acquisitions=1500.0,
    debt_issued=2000.0,
    debt_repaid=1000.0,
    dividends_paid=3000.0,
    share_repurchases=500.0,
)

print(f"Operating Cash Flow   : ₹{cf.operating_cash_flow:,.2f} Cr")
print(f"Free Cash Flow (FCF)  : ₹{cf.free_cash_flow:,.2f} Cr")
print(f"Total Reinvestment    : ₹{cf.reinvestment:,.2f} Cr")
print(f"Financing Requirement : ₹{cf.financing_requirement:,.2f} Cr")
