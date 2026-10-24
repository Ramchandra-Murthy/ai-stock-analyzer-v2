def calculate_rsi(df, period=14):
    """
    Calculate Relative Strength Index (RSI)
    """

    delta = df["Close"].diff()

    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss

    df[f"RSI_{period}"] = 100 - (100 / (1 + rs))

    return df
