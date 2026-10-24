def calculate_histogram(df):
    """
    Calculate the MACD Histogram.

    Histogram = MACD - Signal
    """

    df["Histogram"] = df["MACD"] - df["Signal"]

    return df
