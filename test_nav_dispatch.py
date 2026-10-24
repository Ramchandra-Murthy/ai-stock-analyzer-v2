from services.valuation import get_valuation_dispatcher

dispatcher = get_valuation_dispatcher()

entity = {
    "company_name": "BandraHoldings",
    "currency": "INR",
    "shares_outstanding": 1000.0,
    "holding_company_discount_pct": 0.10,
    "assets": [
        {
            "name": "Commercial Property",
            "category": "PROPERTY",
            "book_value": 50000.0,
            "fair_value": 85000.0,
        }
    ],
    "liabilities": [
        {
            "name": "Bank Debt",
            "category": "LONG_TERM_DEBT",
            "amount": 15000.0,
        }
    ],
}

res = dispatcher.dispatch("NAV", entity)

print(f"Status: {res.valuation_status.value}")
print(f"Entity: {res.entity_name}")
print(f"Equity Value: INR {res.equity_value:,.2f}")
print(f"Implied Share Price: INR {res.diagnostics['share_price']:.2f}")
