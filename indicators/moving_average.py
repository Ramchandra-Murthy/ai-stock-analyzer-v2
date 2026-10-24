def calculate_sma(df, period=20):
    """
    Calculate Simple Moving Average
    """

    column_name = f"SMA_{period}"

    df[column_name] = df["Close"].rolling(window=period).mean()

    return df


def calculate_ema(df, period=20):
    """
    Calculate Exponential Moving Average
    """

    column_name = f"EMA_{period}"

    df[column_name] = df["Close"].ewm(span=period, adjust=False).mean()

    return df
