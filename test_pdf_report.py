from reports.report_generator import ReportGenerator

data = {
    "company": "Reliance Industries Limited",
    "sector": "Energy",
    "industry": "Oil & Gas",
    "price": 1500,
    "market_cap": 20000000000000,
    "currency": "INR",
    "pe": 25,
    "pb": 2.5,
    "eps": 60,
    "roe": 0.15,
    "profit_margin": 0.10,
    "operating_margin": 0.15,
    "dividend_yield": 0.004,
}


generator = ReportGenerator()

pdf_path = generator.generate(
    symbol="RELIANCE",
    data=data,
    investment_score=70,
    technical_score=60,
    fundamental_score=65,
    recommendation="BUY",
    technical_reasons=[
        "MACD bullish",
        "Price above support",
    ],
    fundamental_reasons=[
        "Reasonable valuation",
        "Strong balance sheet",
    ],
    news=[],
)

print("PDF created:")
print(pdf_path)
