def calculate_macd(df):

    ema12 = df["Close"].ewm(span=12, adjust=False).mean()

    ema26 = df["Close"].ewm(span=26, adjust=False).mean()

    df["MACD"] = ema12 - ema26

    df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    df["Histogram"] = df["MACD"] - df["Signal"]

    return df
