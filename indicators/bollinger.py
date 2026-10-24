def calculate_bollinger(df, period=20, std_dev=2):

    sma = df["Close"].rolling(window=period).mean()

    std = df["Close"].rolling(window=period).std(ddof=0)

    df["BB_Middle"] = sma
    df["BB_Upper"] = sma + (std_dev * std)
    df["BB_Lower"] = sma - (std_dev * std)

    return df
