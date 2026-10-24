def portfolio_summary(df):
    """
    Calculate basic portfolio summary metrics.
    """

    if df.empty:
        return {
            "investment": 0,
            "current_value": 0,
            "profit": 0,
            "return": 0,
            "holdings": 0,
        }

    investment = (df["quantity"] * df["buy_price"]).sum()

    current_value = 0

    if "Current Value" in df.columns:
        current_value = df["Current Value"].fillna(0).sum()

    profit = current_value - investment

    if investment > 0:
        returns = (profit / investment) * 100
    else:
        returns = 0

    return {
        "investment": round(investment, 2),
        "current_value": round(current_value, 2),
        "profit": round(profit, 2),
        "return": round(returns, 2),
        "holdings": len(df),
    }
