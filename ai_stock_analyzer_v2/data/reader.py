import pandas as pd

from data.database import connect


def load_stock(symbol):

    conn = connect()

    query = """
        SELECT *
        FROM stock_prices
        WHERE Symbol = ?
        ORDER BY Date
    """

    df = pd.read_sql(query, conn, params=(symbol,))

    conn.close()

    return df
