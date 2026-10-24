from data.database import connect


def save_dataframe(df, symbol):

    conn = connect()
    cur = conn.cursor()

    # Reset index so Date becomes a column
    df = df.reset_index()

    # Remove incomplete rows
    df = df.dropna(subset=["Open", "High", "Low", "Close", "Volume"])

    for _, row in df.iterrows():

        cur.execute(
            """
            INSERT OR REPLACE INTO stock_prices
            VALUES(?,?,?,?,?,?,?)
            """,
            (
                str(row["Date"].date()),
                symbol,
                float(row["Open"]),
                float(row["High"]),
                float(row["Low"]),
                float(row["Close"]),
                int(row["Volume"]),
            ),
        )

    conn.commit()
    conn.close()

    print(f"{symbol} saved to SQLite successfully.")
