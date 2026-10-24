def calculate_support_resistance(df, window=10):
    """
    Calculate simple support and resistance using
    rolling lows and rolling highs.
    """

    df["Support"] = df["Low"].rolling(window=window).min()

    df["Resistance"] = df["High"].rolling(window=window).max()

    return df
