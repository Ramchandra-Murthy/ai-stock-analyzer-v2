from services.financials.balance_sheet import BalanceSheet

bs = BalanceSheet(
    cash=5000.0,
    short_term_investments=3000.0,
    short_term_debt=2000.0,
    long_term_debt=10000.0,
    current_lease_liabilities=500.0,
    long_term_lease_liabilities=1500.0,
    total_equity=50000.0,
)

print(f"Total Cash Resources : ₹{bs.total_cash:,.2f} Cr")
print(f"Total Debt (w/ Leases): ₹{bs.total_debt:,.2f} Cr")
print(f"Net Debt              : ₹{bs.net_debt:,.2f} Cr")
print(f"Debt-to-Equity Ratio  : {bs.debt_to_equity:.4f}")
